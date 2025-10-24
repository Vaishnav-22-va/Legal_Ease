from .models import ServiceCategory

def navbar_categories(request):
    categories = ServiceCategory.objects.prefetch_related('services').all()
    return {'navbar_categories': categories}
