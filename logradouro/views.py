from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Logradouro
from .forms import LogradouroForm


@login_required
def logradouro(request):
    """View para listar e cadastrar logradouros"""
    if request.method == 'POST':
        form = LogradouroForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('logradouro')
    else:
        form = LogradouroForm()

    logradouros = Logradouro.objects.all() 
    return render(request, 'logradouro/logradouro.html', {
        'form': form, 
        'logradouros': logradouros
    })


@login_required
def editar_logradouro(request, pk):
    """View para editar um logradouro existente"""
    logradouro = get_object_or_404(Logradouro, pk=pk)
    if request.method == 'POST':
        form = LogradouroForm(request.POST, instance=logradouro)
        if form.is_valid():
            form.save()
            return redirect('logradouro')
    else:
        form = LogradouroForm(instance=logradouro)

    return render(request, 'logradouro/editar_logradouro.html', {'form': form})


@login_required
def excluir_logradouro(request, pk):
    """View para excluir um logradouro"""
    logradouro = get_object_or_404(Logradouro, pk=pk)
    if request.method == 'POST':
        logradouro.delete()
        return redirect('logradouro')
    return render(request, 'logradouro/confirmar_exclusao.html', {'logradouro': logradouro})


@login_required
def profile_view(request):
    """View para exibir o perfil do usuário"""
    return render(request, 'usuario/profile.html')