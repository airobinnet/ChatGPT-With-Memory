import json
import base64
from graphviz import Digraph
from io import BytesIO


# prompt 
# For context, you can include diagrams by writing [DRAW DIAGRAM], followed by a JSON containing arrays of nodes (with id, label, and type), edges (with from, to, and label), and a summary array (with data). Place all data within double quotes.
data = '''
{
  "nodes": [
    {"id": "input", "label": "Input", "type": "circle"},
    {"id": "processing", "label": "Processing", "type": "rectangle"},
    {"id": "memory", "label": "Memory", "type": "rectangle"},
    {"id": "output", "label": "Output", "type": "circle"}
  ],
  "edges": [
    {"from": "input", "to": "processing", "label": "Data"},
    {"from": "processing", "to": "memory", "label": "Store/Retrieve"},
    {"from": "memory", "to": "processing", "label": "Recall"},
    {"from": "processing", "to": "output", "label": "Response"}
  ],
  "summary": [
    {"data": "this is the summary the diagram"}
  ]
}
'''

data2 = '''
{ 
    "nodes": [ 
        {"id": "1", "label": "Node 1", "type": "circle"}, 
        {"id": "2", "label": "Node 2", "type": "square"}, 
        {"id": "3", "label": "Node 3", "type": "triangle"} 
    ],
    "edges": [ 
        {"from": "1", "to": "2", "label": "Edge 1-2"}, 
        {"from": "2", "to": "3", "label": "Edge 2-3"}, 
        {"from": "3", "to": "1", "label": "Edge 3-1"} 
    ],
    "summary": [ 
        { "data": "This is a simple diagram with 3 nodes and 3 edges."}
    ]
}
'''

def draw_diagram(parsed_data):
    #parsed_data = json.loads(data)
    G = Digraph('G', format='png')

    for node in parsed_data['nodes']:
        shape = 'circle' if node['type'] == 'circle' else 'rectangle'
        color = 'skyblue' if node['type'] == 'circle' else 'palegreen'
        G.node(node['id'], label=node['label'], shape=shape, color=color, style='filled', fontname='Arial', fontsize='12')

    for edge in parsed_data['edges']:
        G.edge(edge['from'], edge['to'], label=edge['label'], fontname='Arial', fontsize='10')

    for summary in parsed_data['summary']:
        G.attr(label=summary['data'], labelloc='b', labeljust='l', fontname='Arial', fontsize='10')

    buf = BytesIO()
    buf.write(G.pipe())
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')

#print(draw_diagram(data2))