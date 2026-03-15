from django.shortcuts import render

# Create your views here.
from django.utils import timezone
from django.db.models import Count
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import QuoteWorksheet
from .serializers import RFQIntakeSerializer, QuoteWorksheetSerializer


class RFQIntakeView(APIView):
    """
    Accepts raw RFQ submissions and initializes a QuoteWorksheet.

    The RFQ text typically originates from customer emails and is stored
    verbatim. Downstream services (LLM parsing, catalog matching, review)
    operate on this worksheet record.

    This endpoint intentionally does NOT perform parsing or matching.
    It only creates the workflow object that enters the quoting pipeline.
    """

    def post(self, request):
        # Validate request payload and enforce API contract
        serializer = RFQIntakeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create the worksheet representing this RFQ request
        # Initial state is "processing" until downstream parsing/matching runs
        worksheet = QuoteWorksheet.objects.create(
            rfq_text=serializer.validated_data["rfq_text"],
            status="processing",
            rfq_source="api",  # Track ingestion channel for analytics/debugging
        )

        # Return the created resource so the client can track the RFQ lifecycle
        response_serializer = QuoteWorksheetSerializer(worksheet)

        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class ActiveQuotesView(APIView):
    """
    Lists all quote worksheets still active in the workflow.

    "Active" = not completed. This includes worksheets currently being:
        - parsed
        - catalog matched
        - reviewed by humans

    Ordered newest-first to prioritize recent RFQs in dashboards/queues.
    """

    def get(self, request):
        worksheets = (
            QuoteWorksheet.objects
            .exclude(status="completed")
            .order_by("-created_at")
        )

        serializer = QuoteWorksheetSerializer(worksheets, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


class CompletedQuotesView(APIView):
    """
    Lists RFQs that have exited the quoting pipeline.

    These records are typically used for:
        - reporting
        - historical analysis
        - quote audit trails
    """

    def get(self, request):
        worksheets = (
            QuoteWorksheet.objects
            .filter(status="completed")
            .order_by("-created_at")
        )

        serializer = QuoteWorksheetSerializer(worksheets, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


class CompleteQuoteView(APIView):
    """
    Finalizes a quote worksheet.

    This represents the terminal state of the quoting workflow.
    Once completed, the worksheet exits the active processing queue.
    """

    def post(self, request, pk):
        try:
            # Lookup worksheet being finalized
            worksheet = QuoteWorksheet.objects.get(pk=pk)

        except QuoteWorksheet.DoesNotExist:
            # Explicit error response for invalid worksheet references
            return Response(
                {"detail": "Quote worksheet not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Transition worksheet to terminal workflow state
        worksheet.status = "completed"

        # Capture completion timestamp for operational metrics
        worksheet.completed_at = timezone.now()

        worksheet.save()

        serializer = QuoteWorksheetSerializer(worksheet)

        return Response(serializer.data, status=status.HTTP_200_OK)


class StatsSummaryView(APIView):
    """
    Provides lightweight operational metrics for the quoting system.

    Used by dashboards or internal tooling to understand pipeline health:
        - backlog size
        - processing load
        - review queue
        - throughput
    """

    def get(self, request):
        # Total RFQs processed by the system
        total_count = QuoteWorksheet.objects.count()

        # Worksheets currently moving through automated processing
        processing_count = QuoteWorksheet.objects.filter(status="processing").count()

        # Worksheets requiring manual intervention
        needs_review_count = QuoteWorksheet.objects.filter(status="needs_review").count()

        # Fully completed RFQs
        completed_count = QuoteWorksheet.objects.filter(status="completed").count()

        return Response(
            {
                "total_quotes": total_count,
                "processing_quotes": processing_count,
                "needs_review_quotes": needs_review_count,
                "completed_quotes": completed_count,
            },
            status=status.HTTP_200_OK,
        )