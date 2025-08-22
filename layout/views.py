from django.contrib.auth.decorators import login_required
from django.shortcuts import render



@login_required
def layout(request):
    return render(request, 'layout/base.html')
@login_required
def dasboard(request):
    return render(request, 'layout/content/dashbord.html')