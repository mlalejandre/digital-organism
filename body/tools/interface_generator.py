#!/usr/bin/env python3
"""
tools/interface_generator.py - Generador del contrato de interfaz (MCP/JSON-Schema)
Inspecciona las herramientas creadas en tools/ y genera memory/interface.json
para que un agente orquestador superior conozca exactamente cómo usarlas.
"""
import os
import ast
import json
from pathlib import Path

INFRA_FILES = {
    "web_search.py", "web_reader.py", "knowledge_base.py", 
    "memory_indexer.py", "utils.py", "verify_all.py", 
    "self_healing_loop.py", "interface_generator.py", "run_case.py", "run_tests.py", "researcher.py"
}

def analyze_tool(filepath: Path) -> dict:
    with open(filepath, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())
        
    docstring = ast.get_docstring(tree) or "Herramienta especializada."
    functions = []
    
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            fn_doc = ast.get_docstring(node) or "Función de ejecución."
            args = [a.arg for a in node.args.args if a.arg != "self"]
            functions.append({
                "name": node.name,
                "description": fn_doc,
                "parameters": args
            })
            
    return {
        "file": filepath.name,
        "description": docstring,
        "functions": functions
    }

def generate_interface():
    tools_dir = Path("tools")
    memory_dir = Path("memory")
    tools_list = []
    
    if tools_dir.exists():
        for file in sorted(tools_dir.glob("*.py")):
            if file.name not in INFRA_FILES and not file.name.startswith("test_"):
                try:
                    tools_list.append(analyze_tool(file))
                except Exception as e:
                    print(f"Error analizando {file.name}: {e}")
                    
    # Leer el estado para conocer la especialidad
    state_file = memory_dir / "state.json"
    specialization = "especialista_autonomo"
    if state_file.exists():
        try:
            with open(state_file, "r") as sf:
                specialization = json.load(sf).get("especialidad", specialization)
        except Exception:
            pass
            
    interface_manifest = {
        "subagent_name": f"Subagent_{specialization}",
        "specialization": specialization,
        "protocol_version": "1.0-mcp",
        "description": f"Subagente experto especializado en {specialization}.",
        "available_tools": tools_list,
        "entrypoint_guide": "Ejecutar mediante EXECUTE('tools/<script>.py', [args])"
    }
    
    out_path = memory_dir / "interface.json"
    with open(out_path, "w", encoding="utf-8") as out:
        json.dump(interface_manifest, out, indent=2, ensure_ascii=False)
        
    print(f"Contrato de interfaz generado con éxito en: {out_path}")
    print(f"Total de herramientas expuestas al orquestador: {len(tools_list)}")

if __name__ == "__main__":
    generate_interface()
