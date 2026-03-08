# utils/pagination.py
from django.core.paginator import Paginator, EmptyPage
from api.app.base.http.response import BaseResponse


class PaginationHelper:
    @staticmethod
    def paginate_queryset(queryset, request, serializer_class):
        """
        Pagination tool method

        Args:
            queryset: Query set
            request: Request object
            serializer_class: Serializer class
        """
        # Get pagination parameters
        page_num = int(request.GET.get('page_num', 1))
        page_size = int(request.GET.get('page_size', 10))
        # If query is empty, need to return empty data
        if not queryset:
            return BaseResponse.success(data={
                "list": [],
                "total": 0,
                "page_num": page_num,
                "page_size": page_size,
            })
        # Sort in reverse chronological order (default to use create_time field, if not available, try created_at)
        if hasattr(queryset.model, 'create_time'):
            queryset = queryset.order_by('-create_time')

        # Create paginator
        paginator = Paginator(queryset, page_size)
        try:
            page_obj = paginator.page(page_num)
        except EmptyPage:
            # If page number is out of range, return empty data
            return BaseResponse.success(data={
                "list": [],
                "total": paginator.count,
                "page_num": page_num,
                "page_size": page_size,
            })
        data = serializer_class(page_obj.object_list, many=True).data

        return BaseResponse.success(data={
            "list": data,
            "total": paginator.count,  # Total count
            "page_num": page_num,  # Current page
            "page_size": page_size  # Page size
        })
