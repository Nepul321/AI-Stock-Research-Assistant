from django.shortcuts import render
from .api.main import *


def HomeView(request, *args, **kwargs):
	template = "home.html"

	# print(test_api("Apple")['result'][0])
	context = {

	}

	return render(request, template, context)