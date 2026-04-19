import os

css_addon = """
    /* --- Global Beautification --- */
    body {
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      letter-spacing: 0.15px;
    }
    .shell {
      animation: fadeIn 0.4s cubic-bezier(0.4, 0, 0.2, 1) forwards;
    }
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(12px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .panel-box, .hero-box, .product-card, .metric-card, .box, .card, .toolbar {
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      border: 1px solid rgba(255, 255, 255, 0.4);
    }
    .panel-box, .product-card, .metric-card, .box, .card, .toolbar {
      background: rgba(255, 255, 255, 0.8) !important;
    }
    .hero-box {
      border: none;
    }
    .product-card:hover, .metric-card:hover, .box:hover, .card:hover, .toolbar:hover {
      transform: translateY(-4px);
      box-shadow: 0 15px 35px rgba(0,0,0,0.08);
      z-index: 2;
      border-color: rgba(255, 255, 255, 0.8);
    }
    .button {
      border-radius: 8px;
      transition: all 0.2s ease;
      font-weight: 500;
    }
    .button:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }
    .button:active {
      transform: translateY(0);
    }
    table.table {
      background-color: rgba(255, 255, 255, 0.65) !important;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 2px 10px rgba(0,0,0,0.03);
    }
    table.table th {
      background-color: rgba(255, 255, 255, 0.85) !important;
      font-weight: 600;
      border-bottom: 2px solid rgba(0,0,0,0.05);
      border-top: none;
    }
    table.table td {
      border-bottom: 1px solid rgba(0,0,0,0.03);
      vertical-align: middle;
    }
    table.table tbody tr:hover {
      background-color: rgba(255, 255, 255, 0.9) !important;
    }
    .input, .textarea, .select select {
      border-radius: 8px;
      box-shadow: inset 0 1px 3px rgba(0,0,0,0.03);
      transition: all 0.3s ease;
      border: 1px solid rgba(0,0,0,0.1);
      background-color: rgba(255, 255, 255, 0.85);
    }
    .input:focus, .textarea:focus, .select select:focus {
      box-shadow: 0 0 0 0.15rem rgba(62,142,208,0.25);
      border-color: rgba(62,142,208,0.6);
      background-color: rgba(255, 255, 255, 1);
    }
    .tag {
      border-radius: 6px;
      font-weight: 500;
    }
"""

template_dir = r"c:\code\202602\0414\new300\DjangoProject\templates"
exclude = ["Login.html", "Register.html"]

for root, _, files in os.walk(template_dir):
    for file in files:
        if file.endswith(".html") and file not in exclude:
            path = os.path.join(root, file)
            if "includes" in path.replace("\\", "/"): continue
            
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                
            if "/* --- Global Beautification --- */" in content:
                print(f"Skipping {file}")
                continue
                
            new_content = content.replace("</style>", css_addon + "</style>")
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"Patched {file}")
