from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status, viewsets
from rest_framework.filters import OrderingFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsOwnerRole, IsSeekerRole

from .filters import PropertyFilter
from .models import Favorite, Property, PropertyPhoto, Status
from .serializers import PropertyCardSerializer, PropertyCreateSerializer, PropertyDetailSerializer


class PropertyPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 48


def published_properties():
    """The only listings the public can see. Photos come prefetched and ordered."""
    return Property.objects.filter(status=Status.PUBLISHED).prefetch_related(
        Prefetch('photos', queryset=PropertyPhoto.objects.order_by('position', 'id'))
    )


class PropertyViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """
    GET  /api/properties          public, published only
    GET  /api/properties/:slug    public, published only
    POST /api/properties          owner accounts, multipart, always saved as pending
    """

    lookup_field = 'slug'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = PropertyFilter
    ordering_fields = ['price', 'published_at']
    ordering = ['-published_at', '-id']
    pagination_class = PropertyPagination
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        return published_properties()

    def get_permissions(self):
        return [IsOwnerRole()] if self.action == 'create' else [AllowAny()]

    def get_serializer_class(self):
        if self.action == 'create':
            return PropertyCreateSerializer
        return PropertyDetailSerializer if self.action == 'retrieve' else PropertyCardSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        prop = serializer.save()
        prop = Property.objects.prefetch_related('photos').get(pk=prop.pk)
        data = PropertyDetailSerializer(prop, context=self.get_serializer_context()).data
        return Response(data, status=status.HTTP_201_CREATED)


class FavoriteListView(APIView):
    """GET /api/favorites: the signed-in seeker's saved properties (published ones only)."""

    permission_classes = [IsSeekerRole]

    def get(self, request):
        saved = published_properties().filter(favorites__user=request.user).order_by('-favorites__created_at')
        return Response(PropertyCardSerializer(saved, many=True, context={'request': request}).data)


class FavoriteDetailView(APIView):
    """POST /api/favorites/:id saves a property; DELETE removes it."""

    permission_classes = [IsSeekerRole]

    def post(self, request, pk):
        prop = get_object_or_404(Property, pk=pk, status=Status.PUBLISHED)
        _, created = Favorite.objects.get_or_create(user=request.user, property=prop)
        return Response(
            {'id': prop.pk, 'favorited': True},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def delete(self, request, pk):
        Favorite.objects.filter(user=request.user, property_id=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
