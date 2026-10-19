from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from .models import Watchlist

from .forms import WatchlistForm

@login_required
def create_watchlist(request):
    form = WatchlistForm()
    if request.method == 'POST':
        form = WatchlistForm(request.POST)
        if form.is_valid():
            watchlist = form.save(commit=False)
            watchlist.user = request.user
            watchlist.save()
            return redirect('home')
    context = {'form': form}
    return render(request, 'watchlists/create.html', context)

@login_required
def watchlist_detail_delete(request, pk):
    watchlist = Watchlist.objects.get(pk=pk)
    if not watchlist:
        return redirect('home')
    if watchlist.user != request.user:
        return redirect('home')
    if request.method == 'POST':
        watchlist.delete()
        return redirect('home')
    context = {'watchlist': watchlist}
    return render(request, 'watchlists/detail_delete.html', context)

@login_required
def watchlist_update(request, pk):
    watchlist = Watchlist.objects.get(pk=pk)
    if not watchlist:
        return redirect('home')
    if watchlist.user != request.user:
        return redirect('home')
    form = WatchlistForm(instance=watchlist)
    if request.method == 'POST':
        form = WatchlistForm(request.POST, instance=watchlist)
        if form.is_valid():
            form.save()
            return redirect('home')
    context = {'form': form, 'watchlist': watchlist}
    return render(request, 'watchlists/update.html', context)

@login_required
def remove_stock_from_watchlist(request, watchlist_id, stock_id):
    watchlist = Watchlist.objects.get(id=watchlist_id)
    if not watchlist:
        return redirect('home')
    if watchlist.user != request.user:
        return redirect('home')
    watchlist.stocks.remove(stock_id)
    return redirect('watchlist_detail_delete', pk=watchlist_id)