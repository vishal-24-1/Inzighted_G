from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ..serializers import RagQuerySerializer
from ..rag_query import query_rag


class QueryView(APIView):
    """
    API view to handle RAG queries.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = RagQuerySerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            user_id = str(request.user.id)
            query = serializer.validated_data['query']

            response = query_rag(user_id, query)

            return Response({"response": response})
        return Response(serializer.errors, status=400)


__all__ = ['QueryView']
