from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404


from .models import FichaEPI
from .forms import FichaEPIForm
from .models import EquipamentosSeguranca
from .forms import EquipamentosSegurancaForm
from django.utils import timezone


@login_required
def seguranca_trabalho(request):
    return render(request, 'seguranca_trabalho/seguranca_trabalho.html')

@login_required
def profile_view(request):
    return render(request, 'usuario/profile.html')

@login_required
def pesquisar_ficha(request):
    fichas = FichaEPI.objects.all()
    return render(request, 'pesquisar_ficha.html', {'fichas': fichas})
@login_required
def cadastrar_ficha_epi(request):
    if request.method == 'POST':
        form = FichaEPIForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('pesquisar_ficha')
    else:
        form = FichaEPIForm()
    return render(request, 'cadastrar_ficha_epi.html', {'form': form})
@login_required
def editar_ficha_epi(request, id):
    ficha = get_object_or_404(FichaEPI, id=id)
    if request.method == 'POST':
        form = FichaEPIForm(request.POST, instance=ficha)
        if form.is_valid():
            form.save()
            return redirect('pesquisar_ficha')
    else:
        form = FichaEPIForm(instance=ficha)
    return render(request, 'cadastrar_ficha_epi.html', {'form': form})
@login_required
def deletar_ficha_epi(request, id):
    ficha = get_object_or_404(FichaEPI, id=id)
    ficha.delete()
    return redirect('pesquisar_ficha')

#Equipamento EPI
# Listar todos os equipamentos
@login_required
def listar_equipamentos(request):
    equipamentos = EquipamentosSeguranca.objects.all()
    return render(request, 'listar_equipamentos.html', {'equipamentos': equipamentos})

# Cadastrar novo equipamento
@login_required
def cadastrar_equipamento(request):
    if request.method == 'POST':
        form = EquipamentosSegurancaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('listar_equipamentos')
    else:
        form = EquipamentosSegurancaForm()
    return render(request, 'cadastrar_equipamento.html', {'form': form})

# Editar equipamento existente
@login_required
def editar_equipamento(request, id):
    equipamento = get_object_or_404(EquipamentosSeguranca, id=id)
    if request.method == 'POST':
        form = EquipamentosSegurancaForm(request.POST, instance=equipamento)
        if form.is_valid():
            form.save()
            return redirect('listar_equipamentos')
    else:
        form = EquipamentosSegurancaForm(instance=equipamento)
    return render(request, 'editar_equipamento.html', {'form': form, 'equipamento': equipamento})

# Excluir equipamento
@login_required
def excluir_equipamento(request, id):
    equipamento = get_object_or_404(EquipamentosSeguranca, id=id)
    equipamento.delete()
    return redirect('listar_equipamentos')

