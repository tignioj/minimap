def generate_docs_array2(cls):
    methods_docs = []

    # 获取当前类定义的方法，不包括父类的方法
    for method_name, method in cls.__dict__.items():
        # 确保它是一个函数或方法
        if callable(method) and not method_name.startswith("__"):
            doc = method.__doc__
            sps = doc.split("\n")
            sps = [s.strip() for s in sps if s.strip()]
            params = []
            returns = []
            for sp in sps:
                if sp.startswith(":param"):
                    params.append(sp[sp.index(" ")+1:])
                elif sp.startswith(":return:"):
                    try: returns.append(sp[sp.index(" ")+1:])
                    except(ValueError, IndexError): pass
            # summary = sps[0] + " (" + ", ".join(params) + ")"
            summary = sps[0]
            # if len(params) > 0: summary = sps[0] + " 参数(" + " ; ".join(params) + ")"
            methods_docs.append({
                "method_name": method_name,
                "summary": summary,
                "params": params,
                "return": None if len(returns) == 0 else returns
            })
    return methods_docs


if __name__ == '__main__':
    from fightmapper.BaseFightMapper import BaseFightMapper
    md = generate_docs_array2(BaseFightMapper)
    import json
    with open('fightmapper.json', 'w', encoding="utf8") as f:
        json.dump(md, f, ensure_ascii=False, indent=4)