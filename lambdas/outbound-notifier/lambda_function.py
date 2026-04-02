import json
import os
import requests
import boto3

ssm = boto3.client('ssm')
REST_API_KEY = "-------------" # 사용자님의 키

def get_refresh_token():
    # 금고에서 리프레시 토큰 가져오기
    return ssm.get_parameter(Name='/smart-home/kakao/refresh-token')['Parameter']['Value']

def update_refresh_token(new_token):
    # 금고에 새로운 리프레시 토큰 저장 (갱신용)
    ssm.put_parameter(Name='/smart-home/kakao/refresh-token', Value=new_token, Type='String', Overwrite=True)

def get_access_token():
    # 리프레시 토큰으로 따끈따끈한 액세스 토큰 받기
    refresh_token = get_refresh_token()
    url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": REST_API_KEY,
        "refresh_token": refresh_token,
        "client_secret": "M5rS2S2Mzjqj2SL1CrUGuy6iAzq5HyFD"
    }
    response = requests.post(url, data=data).json()

    # 만약 카카오가 새 리프레시 토큰을 줬다면 금고 업데이트 (무한 동력 핵심)
    if 'refresh_token' in response:
        update_refresh_token(response['refresh_token'])

    return response['access_token']

def handler(event, context):
    # 1. EventBridge로부터 누락 물건 정보 받기
    detail = event.get('detail', {})
    missing_items = detail.get('missing_items', [])

    if not missing_items:
        return "No missing items."

    # 2. 카톡 메시지 내용 만들기
    message_text = f"🚨 [스마트홈 알림]\n외출 시 물건을 확인하세요!\n누락 품목: {', '.join(missing_items)}"

    # 3. 카카오 API 호출 (나에게 보내기)
    access_token = get_access_token()
    header = {"Authorization": f"Bearer {access_token}"}
    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    post_data = {
        "template_object": json.dumps({
            "object_type": "text",
            "text": message_text,
            "link": {"web_url": "https://localhost:3000", "mobile_web_url": "https://localhost:3000"},
            "button_title": "확인하기"
        })
    }

    res = requests.post(url, headers=header, data=post_data)

    if res.status_code == 200:
        print("✅ 카톡 발송 성공!")
        return "Success"
    else:
        print(f"❌ 카톡 발송 실패: {res.text}")
        return "Fail"