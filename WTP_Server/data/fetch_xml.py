import json
import area_code_dict

def map_area_code_to_children(parent_code: str) -> None:
    try:
        # area.jsonをURLから取得
        area_json = area_code_dict.fetch_area_json()
        if not area_json:
            print("エリアコードJSONの取得に失敗したため、処理を中止します")
            return {}

        result = {}
        processed_codes_class10s = set()
        processed_codes_class15s = set()

        def find_in_json(code: str, target_type: str = None) -> tuple[dict, str]:
            """officesとclass10s、class15sからコードを検索
            
            Args:
                code (str): 検索するコード
                target_type (str): 検索対象のタイプ（'class15s'または'class10s'）
            """
            # 特定のタイプが指定されている場合、そのタイプのみ検索
            if target_type == 'class15s':
                if code in area_json.get('class15s', {}):
                    print(f"class15sで発見: {code}")
                    return area_json['class15s'][code], 'class15s'
                print(f"コード {code} がclass15sで見つかりません")
                return None, None
                
            elif target_type == 'class10s':
                if code in area_json.get('class10s', {}):
                    print(f"class10sで発見: {code}")
                    return area_json['class10s'][code], 'class10s'
                print(f"コード {code} がclass10sで見つかりません")
                return None, None
            
            # タイプ指定がない場合は全カテゴリーを検索
            if code in area_json.get('class10s', {}):
                print(f"class10sで発見: {code}")
                return area_json['class10s'][code], 'class10s'
            
            elif code in area_json.get('class15s', {}):
                print(f"class15sで発見: {code}")
                return area_json['class15s'][code], 'class15s'
            
            elif code in area_json.get('offices', {}):
                print(f"officesで発見: {code}")
                return area_json['offices'][code], 'offices'
            
            print(f"コード {code} が見つかりません")
            return None, None

        def collect_leaf_codes(code: str, is_root: bool = False) -> None:
            """class10sのコードをキーとして末端コードを収集"""
            if code in processed_codes_class10s:
                print(f"コード {code} は既に処理済みのためスキップします")
                return

            processed_codes_class10s.add(code)
            
            # ルートコードの場合は全カテゴリーを検索、それ以外はclass10sのみ
            node, source = find_in_json(code, None if is_root else 'class10s')
            if not node:
                return
            
            children = node.get('children', [])
            print(f'子コード{children}')
            
            if source == 'class10s':
                # class10sの場合は新しいキーを作成
                result[code] = []
                # 子コードを処理
                for child in children:
                    collect_class15_codes(child, code)
            else:
                # それ以外の場合は再帰的に探索
                for child in children:
                    collect_leaf_codes(child)

        def collect_class15_codes(code: str, parent_class10: str) -> None:
            """class15sの末端コードを収集してclass10sのキーに追加"""
            if code in processed_codes_class15s:
                return

            processed_codes_class15s.add(code)
            
            # class15sとして検索
            node, source = find_in_json(code, target_type='class15s')
            if not node:
                return
            
            if source == 'class15s':
                # class15sの場合は末端のコードをclass10sのキーに追加
                result[parent_class10].extend(node.get('children', []))
            else:
                # それ以外の場合は再帰的に探索
                for child in node.get('children', []):
                    collect_class15_codes(child, parent_class10)

        # コードの収集を開始（最初のコードはルートとして扱う）
        collect_leaf_codes(parent_code, is_root=True)

        print(f"class10sのコードをキーとする末端コードを正常に保存しました")

        return result

    except Exception as e:
        print(f"エラーが発生しました: {e}")

def fetch_all_area_code():
    conn, cur = area_code_dict.postgre_conn()
    if conn and cur:
        try:
            # データベース操作を実行
            cur.execute("SELECT code FROM districts;")
            codes = cur.fetchall()
            
            all_children_code = {}
            for (code,) in codes:
                all_children_code.update(map_area_code_to_children(code))

            # postgre_child_code.jsonを読み込む
            with open('wtp/resources/postgre_child_code.json', 'w', encoding='utf-8') as f:
                json.dump(all_children_code, f, ensure_ascii=False, indent=4)

            for (code,) in codes:
                # 対応する子コードを取得（存在しない場合は空配列）
                child_codes = all_children_code.get(code, [])
                
                # PostgreSQL配列形式に変換
                child_codes_array = '{' + ','.join(f'"{code}"' for code in child_codes) + '}'

                # child_codeカラムを更新
                update_query = """
                    UPDATE districts 
                    SET child_codes = %s 
                    WHERE code = %s;
                """
                cur.execute(update_query, (child_codes_array, code))
                print(f"コード {code} の子コードを更新: {child_codes}")
                
            # 変更をコミット
            conn.commit()

        finally:
            # 接続を閉じる
            area_code_dict.close_postgre_conn(conn, cur)

fetch_all_area_code()