from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth import logout, login
from django.views.decorators.debug import sensitive_post_parameters
from django.utils.decorators import method_decorator
from django.views.generic import View

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .graph_models import *
from .forms import CommentForm, UserForm, PostForm
from .utils import are_passwords_matching, create_post, create_user_node, delete_all_nodes

config.DATABASE_URL = 'bolt://neo4j:password@localhost:7687'


def index(request):
    context = dict(username=request.user.username)
    return render(request, "app/index.html", context)


def post_list(request):
    posts = list()
    post_nodes = Post.nodes
    for node in post_nodes:
        # TODO fixing this so as we don't create new collection each time
        post = dict(
            name=node.name,
            uid=node.uid,
            description=node.description,
            photo=node.photo.single().name,
            author=node.author.single().name,
            comments=node.comments.all()
        )
        posts.append(post)
        print(node.comments.all())
    context = dict(posts=posts)
    return render(request, 'app/post_list.html', context)


def graphdb_test(request):
    """Just playground"""
    delete_all_nodes(User.nodes.filter(name="admin"))
    create_user_node("admin")
    print(User.nodes.get(name="admin"))
    return render(request, "app/index.html", {})


class PostCreate(View):
    form_class = PostForm
    template_name = "app/post_create.html"

    def get(self, request):
        """Displaying blank form"""
        form = self.form_class(None)
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            description = form.cleaned_data['description']
            username = self.request.user.username
            author = User.nodes.get(name=username)
            photo = Photo.nodes.get(name="sea")  # temporarily
            create_post(name, description, author, photo)
            messages.success(self.request, "Post has been added!")
            return redirect('post-list')
        else:
            messages.error(self.request, "Invalid form")

        return render(request, self.template_name, {'form': form})


def comment_create(request, post_uid):
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            author = User.nodes.get(name=request.user.username)
            post = Post.nodes.get(uid=post_uid)
            text = form.cleaned_data['comment_text']
            comment = Comment(text=text).save()
            comment.author.connect(author)
            comment.post.connect(post)
            comment.save()
            post.comments.connect(comment)
            post.save()
            return redirect('post-list')
    else:
        form = CommentForm()

    return render(request, 'app/comment_create.html', {'form': form})


@api_view(['POST', 'GET'])
def rest_comment_add(request):
    if request.method == 'GET':
        return Response({'hello': 'world'}, status=status.HTTP_200_OK)
    return Response(request.data, status=status.HTTP_200_OK)



class RegisterView(View):
    form_class = UserForm
    template_name = "registration/registration.html"

    def get(self, request):
        """Displaying blank form"""
        form = self.form_class(None)
        return render(request, self.template_name, {'form': form})

    @method_decorator(sensitive_post_parameters())
    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            if are_passwords_matching(form):
                user = create_and_authenticate_user(form)
                if user is not None:
                    create_user_node(user.username)
                    messages.success(self.request, "User has been created!")
                    login(self.request, user)
                    return redirect('index')
                else:
                    messages.error(self.request, "Invalid email or password")
            else:
                form.add_error('password_confirm', 'Passwords do not match')

        return render(request, self.template_name, {'form': form})


def logout_view(request):
    logout(request)
    return render(request, 'registration/logged_out.html', {})
