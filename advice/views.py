from django.shortcuts import render

def AdviceListView(request, *args, **kwargs):
    template = "advice/advice.html"
    context = {

    }

    return render(request, template, context)