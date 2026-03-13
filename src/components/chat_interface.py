from dash import html, dcc
import dash_bootstrap_components as dbc

def create_chat_interface():
    """
    Creates the Offcanvas sidebar for the Data Journalist agent.
    """
    return html.Div([
        # Toggle Button (Floating at the bottom right, shifted left)
        dbc.Button(
            html.I(className="fas fa-robot"),
            id="open-chat",
            color="primary",
            className="rounded-circle shadow-lg",
            style={
                "position": "fixed",
                "bottom": "20px",
                "right": "80px",
                "width": "60px",
                "height": "60px",
                "zIndex": "1000",
                "fontSize": "24px",
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "center"
            }
        ),
        
        # The Sidebar
        dbc.Offcanvas(
            [
                html.Div(
                    id="chat-history",
                    style={
                        "height": "70vh",
                        "overflowY": "auto",
                        "display": "flex",
                        "flexDirection": "column",
                        "gap": "10px",
                        "padding": "10px",
                        "border": "1px solid #ddd",
                        "borderRadius": "5px",
                        "marginBottom": "15px",
                        "backgroundColor": "#f9f9f9"
                    }
                ),
                
                dbc.InputGroup([
                    dbc.Textarea(
                        id="chat-input",
                        placeholder="Ask me something about the data...",
                        rows=1,
                        style={"resize": "none"},
                        autoFocus=True
                    ),
                    dbc.Button(
                        html.I(className="fas fa-paper-plane"),
                        id="send-chat",
                        color="primary",
                        style={"display": "flex", "alignItems": "center", "justifyContent": "center"}
                    ),
                ]),
                
                html.Hr(),
                
                html.Div([
                    dbc.Button(
                        "Download Executive Summary",
                        id="download-summary-btn",
                        color="secondary",
                        outline=True,
                        className="w-100 mb-2"
                    ),
                    dcc.Download(id="download-summary-data")
                ]),
                
                # Stores for state management
                dcc.Store(id="chat-history-store", data=[]),
                dcc.Store(id="pending-query-store", data=None)
            ],
            id="chat-sidebar",
            title="Data Journalist AI",
            is_open=False,
            placement="end",
            style={"width": "450px"}
        )
    ])

def format_message(msg):
    """Formats a message bubble for the chat history."""
    is_user = msg['role'] == 'user'
    is_thinking = msg['content'] == "_THINKING_"
    
    content = msg['content']
    if is_thinking:
        content = html.Div([
            html.Span(".", className="thinking-dot"),
            html.Span(".", className="thinking-dot"),
            html.Span(".", className="thinking-dot"),
        ], className="thinking-container")

    return html.Div(
        [
            html.Div(
                content,
                className=f"chat-bubble {'user' if is_user else 'agent'}",
                style={
                    "padding": "10px 15px",
                    "borderRadius": "15px",
                    "maxWidth": "85%",
                    "fontSize": "14px",
                    "alignSelf": "flex-end" if is_user else "flex-start",
                    "backgroundColor": "#007bff" if is_user else "#e9ecef",
                    "color": "white" if is_user else "black",
                    "boxShadow": "0 2px 5px rgba(0,0,0,0.1)",
                    "whiteSpace": "pre-wrap"
                }
            )
        ],
        style={
            "display": "flex",
            "flexDirection": "column",
            "alignItems": "flex-end" if is_user else "flex-start",
            "width": "100%",
            "marginBottom": "10px"
        }
    )
