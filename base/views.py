from django.shortcuts import render
from .api.main import *


def HomeView(request, *args, **kwargs):
	template = "base/home.html"
	context = {

	}

	return render(request, template, context)