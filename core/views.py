from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login
from .forms import SignUpForm

def home(request):
    return render(request, "core/home.html")

def signup(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created. Welcome!")
            return redirect("home")
        else:
            messages.error(request, "Please fix the errors below and try again.")
    else:
        form = SignUpForm()
    return render(request, "core/signup.html", {"form": form})
