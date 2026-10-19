from django.db.models import Q
from django_filters import rest_framework as filters

from .models import Property


class PropertyFilter(filters.FilterSet):
    """GET /api/properties?state&city&q&max_price&bedrooms (plus type)."""

    state = filters.CharFilter(field_name='state', lookup_expr='iexact')
    city = filters.CharFilter(field_name='city', lookup_expr='icontains')
    type = filters.CharFilter(field_name='property_type', lookup_expr='iexact')
    max_price = filters.NumberFilter(field_name='price', lookup_expr='lte')
    # "bedrooms=2" means 2 or more, which is how the search form reads.
    bedrooms = filters.NumberFilter(field_name='bedrooms', lookup_expr='gte')
    q = filters.CharFilter(method='search')

    class Meta:
        model = Property
        fields: list[str] = []

    def search(self, queryset, name, value):
        # Every word must match somewhere, so "onitsha flat" narrows rather than widens.
        for term in value.split()[:6]:
            queryset = queryset.filter(
                Q(title__icontains=term)
                | Q(city__icontains=term)
                | Q(state__icontains=term)
                | Q(address__icontains=term)
                | Q(description__icontains=term)
            )
        return queryset
