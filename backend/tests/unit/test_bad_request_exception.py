import pytest
from fastapi import status
from app.core.exceptions import BadRequestException, AppException


def test_bad_request_exception_default_message():
    """Test BadRequestException with default message"""
    exc = BadRequestException()
    assert exc.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.message == "请求参数错误"
    assert exc.detail == "请求参数错误"


def test_bad_request_exception_custom_message():
    """Test BadRequestException with custom message"""
    exc = BadRequestException(message="自定义错误消息")
    assert exc.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.message == "自定义错误消息"
    assert exc.detail == "自定义错误消息"


def test_bad_request_exception_inherits_from_app_exception():
    """Test BadRequestException inherits from AppException"""
    exc = BadRequestException()
    assert isinstance(exc, AppException)
    assert isinstance(exc, Exception)
