import json
import pymysql
import boto3

# EventBridge 사용을 위한 클라이언트
events = boto3.client('events')

def handler(event, context):
    # 1. API Gateway로부터 받은 데이터 파싱
    body = json.loads(event.get('body', '{}'))
    user_id = body.get('user_id', 'team5_user')
    scanned_tags = body.get('tags', [])

    # [중요] 여기를 실제 영문/숫자 정보로 교체하세요!
    # 한글("주소", "비번")이 들어가면 latin-1 에러가 납니다.
    db_config = {
        "host": "-----------------", # 실제 엔드포인트
        "user": "admin",
        "password": "-------", # 예: "SecurePass123!"
        "db": "smart_home_db",
        "charset": "utf8mb4" # 한글 물건 이름 처리를 위해 추가
    }

    conn = pymysql.connect(**db_config)

    try:
        with conn.cursor() as cursor:
            # 2. 필수품 리스트 가져오기
            cursor.execute("SELECT tag_id, item_name FROM user_items WHERE user_id = %s AND is_essential = TRUE", (user_id,))
            essentials = cursor.fetchall()

            # 3. 누락된 물건 찾기
            missing_items = []
            for tag_id, item_name in essentials:
                if tag_id not in scanned_tags:
                    missing_items.append(item_name)

            # 4. 누락이 있다면 EventBridge로 신호 보내기
            if missing_items:
                print(f"🚨 누락 발생: {missing_items}")
                events.put_events(
                    Entries=[{
                        'Source': 'smart.home.scanner',
                        'DetailType': 'ItemMissingEvent',
                        'Detail': json.dumps({'user_id': user_id, 'missing_items': missing_items}),
                        'EventBusName': 'ItemScanBus'
                    }]
                )
                return {"statusCode": 200, "body": json.dumps({"message": f"Missing: {missing_items}"})}

        return {"statusCode": 200, "body": json.dumps({"message": "All items present!"})}

    except Exception as e:
        print(f"❌ 실행 에러: {str(e)}")
        return {"statusCode": 500, "body": str(e)}
    finally:
        conn.close()