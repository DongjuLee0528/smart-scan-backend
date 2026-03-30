import json, pymysql, os, re, traceback

# ✅ [수정] 정식 도메인으로 교체 (마지막 / 제외)
ALLOWED_ORIGIN = "https://smartscan-hub.com"

def make_res(success, message, is_kakao=False, buttons=None):
    """보안이 강화되고 도메인이 적용된 응답 생성기"""
    # [보안] CORS를 정식 도메인으로 제한
    res_headers = {
        "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
        "Access-Control-Allow-Headers": "Content-Type, X-Requested-With",
        "Access-Control-Allow-Methods": "POST, OPTIONS"
    }
    
    if not is_kakao:
        return {
            "statusCode": 200, 
            "headers": res_headers, 
            "body": json.dumps({"success": success, "message": str(message)}, ensure_ascii=False)
        }
    
    # 카카오 챗봇 응답 구조 (썸네일 포함 가이드 준수)
    img_url = "https://cdn-icons-png.flaticon.com/512/553/553376.png" 
    res_body = {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "basicCard": {
                        "title": "🏠 SmartHome Hub",
                        "description": str(message),
                        "thumbnail": {"imageUrl": img_url},
                        "buttons": buttons
                    }
                } if buttons else {"simpleText": {"text": str(message)}}
            ]
        }
    }
    return {"statusCode": 200, "headers": res_headers, "body": json.dumps(res_body, ensure_ascii=False)}

def lambda_handler(event, context):
    conn = None
    request_context = event.get('requestContext', {})
    http_info = request_context.get('http', {})
    method = event.get('httpMethod') or http_info.get('method')
    
    # Web 요청 여부 판별
    is_web = 'httpMethod' in event or 'http' in request_context
    
    try:
        if method == 'OPTIONS':
            return make_res(True, "CORS OK")

        conn = pymysql.connect(
            host=os.environ.get('DB_HOST'),
            user=os.environ.get('DB_USER'),
            password=os.environ.get('DB_PASSWORD'),
            db=os.environ.get('DB_NAME'),
            charset='utf8',
            connect_timeout=5
        )
        cursor = conn.cursor()

        raw_body = event.get('body', '{}')
        body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body

        # 🟢 [Web] 기기 등록 로직
        if is_web and ('user_id' in body and 'serial_number' in body):
            u_id = str(body.get('user_id', '')).strip()
            s_n = str(body.get('serial_number', '')).strip().upper()

            if not re.match(r"^SH-\d{4}$", s_n):
                return make_res(False, "올바른 시리얼 번호 형식이 아닙니다. (예: SH-1023)")

            cursor.execute("SELECT serial_number FROM devices WHERE serial_number = %s", (s_n,))
            if not cursor.fetchone():
                return make_res(False, "등록되지 않은 기기 번호입니다. 바닥면을 확인해주세요.")

            sql = """
                INSERT INTO users (user_id, serial_number) 
                VALUES (%s, %s) 
                ON DUPLICATE KEY UPDATE serial_number = %s
            """
            cursor.execute(sql, (u_id, s_n, s_n))
            conn.commit()
            return make_res(True, f"연결 성공! 이제 카카오톡에서 [{s_n}] 기기를 제어할 수 있습니다.")

        # 🔵 [Chatbot] 챗봇 명령어 처리 로직
        else:
            user_req = body.get('userRequest', {})
            utterance = user_req.get('utterance', '').strip()
            user_id = user_req.get('user', {}).get('id', 'unknown')

            cursor.execute("SELECT serial_number FROM users WHERE user_id = %s", (user_id,))
            res = cursor.fetchone()
            
            if not res: 
                # ✅ [수정] 버튼 링크를 정식 도메인 주소로 변경
                web_url = f"{ALLOWED_ORIGIN}?user_id={user_id}"
                return make_res(True, "연결된 기기가 없습니다. 아래 버튼을 눌러 기기를 먼저 등록해주세요.", True, 
                                [{"action": "webLink", "label": "기기 등록하기", "webLinkUrl": web_url}])
            
            reg_sn = res[0]

            if "목록" in utterance:
                sql_items = """
                    SELECT i.item_name, m.label_id 
                    FROM items i 
                    JOIN master_tags m ON i.sticker_id = m.tag_uid 
                    WHERE i.user_id = %s AND i.is_active = 1
                    ORDER BY m.label_id ASC
                """
                cursor.execute(sql_items, (user_id,))
                items = cursor.fetchall()
                
                sql_empty = """
                    SELECT m.label_id FROM master_tags m 
                    LEFT JOIN items i ON m.tag_uid = i.sticker_id AND i.user_id = %s AND i.is_active = 1
                    WHERE m.device_sn = %s AND i.sticker_id IS NULL 
                    ORDER BY m.label_id ASC
                """
                cursor.execute(sql_empty, (user_id, reg_sn))
                empty_list = [str(r[0]) for r in cursor.fetchall()]
                
                msg = f"🏠 [{reg_sn}] 허브 상태\n\n✅ 등록된 물건:\n"
                msg += ("\n".join([f"- {i[0]} ({i[1]}번)" for i in items]) if items else "- 등록된 물건 없음")
                msg += f"\n\n✨ 사용 가능 번호:\n{', '.join(empty_list) if empty_list else '모두 사용 중'}"
                return make_res(True, msg, True)

            elif "추가" in utterance:
                match = re.search(r'([가-힣\w\s]+)\s+추가\s+(\d+)', utterance)
                if match:
                    name, l_id = match.group(1).strip(), match.group(2)
                    cursor.execute("""
                        SELECT i.item_name FROM items i 
                        JOIN master_tags m ON i.sticker_id = m.tag_uid 
                        WHERE i.user_id = %s AND m.label_id = %s AND i.is_active = 1
                    """, (user_id, l_id))
                    if cursor.fetchone():
                        return make_res(True, f"❌ {l_id}번 스티커는 이미 사용 중입니다.", True)
                    
                    cursor.execute("SELECT tag_uid FROM master_tags WHERE device_sn = %s AND label_id = %s", (reg_sn, l_id))
                    tag_row = cursor.fetchone()
                    if tag_row:
                        cursor.execute("INSERT INTO items (item_name, sticker_id, user_id, is_active) VALUES (%s, %s, %s, 1)", (name, tag_row[0], user_id))
                        conn.commit()
                        return make_res(True, f"✅ [{name}]이(가) {l_id}번에 등록되었습니다!", True)
                    return make_res(True, f"❌ 해당 기기에 {l_id}번 스티커가 존재하지 않습니다.", True)
                return make_res(True, "❓ 명령어가 올바르지 않습니다.\n예: 지갑 추가 1", True)

            elif any(word in utterance for word in ["삭제", "제거"]):
                target = utterance.replace("삭제", "").replace("제거", "").replace("물품", "").replace("❌", "").strip()
                if not target: return make_res(True, "❓ 삭제할 물건 이름을 알려주세요.\n예: 지갑 삭제", True)
                
                cursor.execute("UPDATE items SET is_active = 0 WHERE user_id = %s AND item_name = %s AND is_active = 1", (user_id, target))
                conn.commit()
                msg = f"🗑️ [{target}] 삭제 완료!" if cursor.rowcount > 0 else f"❌ 등록된 물건 중 '{target}'을(를) 찾을 수 없습니다."
                return make_res(True, msg, True)

            elif "해제" in utterance:
                cursor.execute("DELETE FROM items WHERE user_id = %s", (user_id,))
                cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
                conn.commit()
                return make_res(True, "🔌 기기 연결이 해제되었습니다. 이용해주셔서 감사합니다.", True)

            else:
                return make_res(True, f"🏠 사용자님 무엇을 도와드릴까요?\n 1.목록 확인\n 2.물건 추가 (예: 지갑 추가 1)\n 3.물건 삭제 (예: 지갑 삭제)\n 4.기기 해제", True)

    except Exception:
        print(traceback.format_exc())
        return make_res(False, "⚠️ 서버 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.", (not is_web))
    finally:
        if conn: conn.close()