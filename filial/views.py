from django.shortcuts import redirect
from django.views import View

class SetFilialView(View):
    def post(self, request, *args, **kwargs):
        filial_id = request.POST.get('filial_id')
        if filial_id:
            request.session['filial_id'] = filial_id
        
        # Redirect to the previous page or a default page
        return redirect(request.META.get('HTTP_REFERER', '/'))
