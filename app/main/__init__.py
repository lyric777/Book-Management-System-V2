from flask import Blueprint
main = Blueprint('main', __name__)

from . import views  # 咱没有自定义错误页面
