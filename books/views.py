from django.db.models import Q

from rest_framework import exceptions as drf_exceptions, viewsets
from rest_framework.response import Response
from urllib.parse import urlencode

from .models import *
from .serializers import *


class BookViewSet(viewsets.ModelViewSet):
    """ This is an API endpoint that allows books to be viewed. """

    lookup_field = 'gutenberg_id'

    queryset = Book.objects.exclude(download_count__isnull=True)
    queryset = queryset.exclude(title__isnull=True)

    serializer_class = BookSerializer

    def get_queryset(self):
        queryset = self.queryset

        sort = self.request.GET.get('sort')
        if sort == 'ascending':
            queryset = queryset.order_by('id')
        elif sort == 'descending':
            queryset = queryset.order_by('-id')
        else:
            queryset = queryset.order_by('-download_count')

        author_year_end = self.request.GET.get('author_year_end')
        try:
            author_year_end = int(author_year_end)
        except:
            author_year_end = None
        if author_year_end is not None:
            queryset = queryset.filter(
                Q(authors__birth_year__lte=author_year_end) |
                Q(authors__death_year__lte=author_year_end)
            )

        author_year_start = self.request.GET.get('author_year_start')
        try:
            author_year_start = int(author_year_start)
        except:
            author_year_start = None
        if author_year_start is not None:
            queryset = queryset.filter(
                Q(authors__birth_year__gte=author_year_start) |
                Q(authors__death_year__gte=author_year_start)
            )

        copyright_parameter = self.request.GET.get('copyright')
        if copyright_parameter is not None:
            copyright_strings = copyright_parameter.split(',')
            copyright_values = set()
            for copyright_string in copyright_strings:
                if copyright_string == 'true':
                    copyright_values.add(True)
                elif copyright_string == 'false':
                    copyright_values.add(False)
                elif copyright_string == 'null':
                    copyright_values.add(None)
            for value in [True, False, None]:
                if value not in copyright_values:
                    queryset = queryset.exclude(copyright=value)

        id_string = self.request.GET.get('ids')
        if id_string is not None:
            ids = id_string.split(',')

            try:
                ids = [int(id) for id in ids]
            except ValueError:
                pass
            else:
                queryset = queryset.filter(gutenberg_id__in=ids)

        language_string = self.request.GET.get('languages')
        if language_string is not None:
            language_codes = [code.lower() for code in language_string.split(',')]
            queryset = queryset.filter(languages__code__in=language_codes)

        mime_type = self.request.GET.get('mime_type')
        if mime_type is not None:
            queryset = queryset.filter(format__mime_type__startswith=mime_type)

        search_string = self.request.GET.get('search')
        if search_string is not None:
            search_terms = search_string.split(' ')
            for term in search_terms[:32]:
                queryset = queryset.filter(
                    Q(authors__name__icontains=term) | Q(title__icontains=term)
                )

        topic = self.request.GET.get('topic')
        if topic is not None:
            queryset = queryset.filter(
                Q(bookshelves__name__icontains=topic) | Q(subjects__name__icontains=topic)
            )

        return queryset.distinct()


class LibraryCategoriesViewSet(viewsets.GenericViewSet):
    """List 5 categories (Bookshelves) each with up to 5 top books."""
    queryset = Bookshelf.objects.all()
    def get_queryset(self):
        return Bookshelf.objects.all()
    def list(self, request):
        try:
            offset = int(self.request.GET.get('offset', '0'))
        except ValueError:
            offset = 0
        if offset < 0:
            offset = 0

        categories_qs = Bookshelf.objects.order_by('name')
        total_categories = categories_qs.count()
        page_size = 5
        categories = list(categories_qs[offset:offset + page_size])

        # Base queryset constraints consistent with books list endpoint
        base_books_qs = Book.objects.exclude(download_count__isnull=True).exclude(title__isnull=True)

        results = []
        for category in categories:
            category_total = (
                base_books_qs
                .filter(bookshelves=category)
                .count()
            )
            books_qs = (
                base_books_qs
                .filter(bookshelves=category)
                .order_by('-download_count')[:5]
            )
            books_data = BookSerializer(books_qs, many=True).data
            base_url = f'{self.request.scheme}://{self.request.get_host()}'
            books_query = urlencode({
                'topic': category.name,
                'sort': 'popular',
                'mime_type': 'application/epub+zip',
                'page_size': 5,
                'page': 2
            })
            next_books_url = f'{base_url}/books?{books_query}'
            results.append({
                'name': category.name,
                'count': category_total,
                'books': books_data,
                'next': next_books_url,
            })

        next_url = None
        next_offset = offset + page_size
        if next_offset < total_categories:
            # Preserve other query params while updating offset
            query_params = self.request.GET.copy()
            query_params['offset'] = str(next_offset)
            next_url = self.request.build_absolute_uri(f'{self.request.path}?{query_params.urlencode()}')

        return Response({
            'results': results,
            'next': next_url,
        })
