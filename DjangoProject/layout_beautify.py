import os

layout_addon = """
    /* --- Flexbox & Typography Tweaks --- */
    .product-card {
      display: flex !important;
      flex-direction: column;
      height: 100%;
    }
    .product-card > img {
      border-top-left-radius: 23px;
      border-top-right-radius: 23px;
      object-fit: cover;
      width: 100%;
      display: block;
    }
    .product-copy, .content {
      display: flex;
      flex-direction: column;
      flex-grow: 1;
      padding: 1.5rem !important;
    }
    .product-copy .level, .content .level {
      margin-top: auto;
      margin-bottom: 0 !important;
    }
    .panel-box, .box {
      padding: 2rem !important;
    }
    @media (max-width: 768px) {
      .panel-box, .box { padding: 1.25rem !important; }
      .metrics { gap: 1rem !important; }
    }
    .metrics {
      gap: 1.5rem;
    }
    .metric-card {
      display: flex;
      flex-direction: column;
      justify-content: center;
      padding: 1.5rem;
    }
    /* Better Form Input Styles */
    .field:not(:last-child) {
      margin-bottom: 1.5rem;
    }
    label.label {
      font-weight: 600;
      color: rgba(0, 0, 0, 0.7);
      margin-bottom: 0.5rem;
      font-size: 0.95rem;
    }
    /* Tables and Pagination Improvements */
    .pagination {
      margin-top: 2rem;
      justify-content: center;
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
                
            if "/* --- Flexbox & Typography Tweaks --- */" in content:
                print(f"Skipping {file}")
                continue
                
            new_content = content.replace("</style>", layout_addon + "</style>")
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"Patched {file}")
