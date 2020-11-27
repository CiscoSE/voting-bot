START_MEETING_TEMPLATE = {
    "type": "AdaptiveCard",
    "version": "1.0",
    "body": [
        {
            "type": "TextBlock",
            "text": "Schůze zahájena",
            "horizontalAlignment": "Center",
            "weight": "Bolder",
            "size": "Medium"
        },
        {
            "type": "RichTextBlock",
            "inlines": [
                {
                    "type": "TextRun",
                    "text": "Aby byl váš hlas započítán, klikněte na tlačítko "
                },
                {
                    "type": "TextRun",
                    "text": "Přítomen",
                    "weight": "Bolder"
                },
                {
                    "type": "TextRun",
                    "text": "."
                }
            ]
        },
        {
            "type": "ActionSet",
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "Přítomen",
                    "id": "present"
                }
            ],
            "horizontalAlignment": "Right"
        },
        {
            "type": "ActionSet",
            "horizontalAlignment": "Right",
            "actions": [
                {
                    "type": "Action.ShowCard",
                    "title": "Ukončit schůzi",
                    "card": {
                        "type": "AdaptiveCard",
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "body": [
                            {
                                "type": "ActionSet",
                                "horizontalAlignment": "Right",
                                "actions": [
                                    {
                                        "type": "Action.Submit",
                                        "title": "Ukončit",
                                        "id": "end_meeting"
                                    }
                                ]
                            }
                        ]
                    }
                }
            ]
        }
    ],
    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json"
}

END_MEETING_TEMPLATE = {
    "type": "AdaptiveCard",
    "version": "1.0",
    "body": [
        {
            "type": "TextBlock",
            "text": "Schůze ukončena",
            "horizontalAlignment": "Center",
            "weight": "Bolder",
            "size": "Medium"
        },
        {
            "type": "ActionSet",
            "horizontalAlignment": "Right",
            "actions": [
                {
                    "type": "Action.ShowCard",
                    "title": "Zahájit novou schůzi",
                    "card": {
                        "type": "AdaptiveCard",
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "body": [
                            {
                                "type": "ActionSet",
                                "horizontalAlignment": "Right",
                                "actions": [
                                    {
                                        "type": "Action.Submit",
                                        "title": "Zahájit",
                                        "id": "start_meeting"
                                    }
                                ]
                            }
                        ]
                    }
                }
            ]
        }
    ],
    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json"
}

SUBMIT_POLL_TEMPLATE = {
    "type": "AdaptiveCard",
    "version": "1.0",
    "body": [
        {
            "type": "TextBlock",
            "text": "Hlasování",
            "weight": "Bolder",
            "horizontalAlignment": "Center"
        },
        {
            "type": "ColumnSet",
            "columns": [
                {
                    "type": "Column",
                    "width": "stretch",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "Téma:",
                            "horizontalAlignment": "Right"
                        }
                    ]
                },
                {
                    "type": "Column",
                    "width": "stretch",
                    "items": [
                        {
                            "type": "Input.Text",
                            "placeholder": "Napište téma",
                            "id": "poll_subject"
                        }
                    ]
                }
            ]
        },
        {
            "type": "ColumnSet",
            "columns": [
                {
                    "type": "Column",
                    "width": "stretch",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "Časový limit:",
                            "horizontalAlignment": "Right"
                        }
                    ]
                },
                {
                    "type": "Column",
                    "width": "stretch",
                    "items": [
                        {
                            "type": "Input.ChoiceSet",
                            "placeholder": "Placeholder text",
                            "choices": [
                                {
                                    "title": "20s",
                                    "value": "20"
                                },
                                {
                                    "title": "30s",
                                    "value": "30"
                                },
                                {
                                    "title": "40s",
                                    "value": "40"
                                },
                                {
                                    "title": "1 minuta",
                                    "value": "60"
                                },
                                {
                                    "title": "2 minuty",
                                    "value": "120"
                                }
                            ],
                            "id": "time_limit",
                            "value": "20"
                        }
                    ]
                }
            ]
        },
        {
            "type": "ActionSet",
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "Zahájit hlasování",
                    "id": "poll_start"
                }
            ],
            "horizontalAlignment": "Right"
        },
        {
            "type": "ActionSet",
            "horizontalAlignment": "Right",
            "actions": [
                {
                    "type": "Action.ShowCard",
                    "title": "Ukončit schůzi",
                    "card": {
                        "type": "AdaptiveCard",
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "body": [
                            {
                                "type": "ActionSet",
                                "horizontalAlignment": "Right",
                                "actions": [
                                    {
                                        "type": "Action.Submit",
                                        "title": "Ukončit",
                                        "id": "end_meeting"
                                    }
                                ]
                            }
                        ]
                    }
                }
            ]
        }
    ],
    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json"
}

POLL_TEMPLATE = {
    "type": "AdaptiveCard",
    "version": "1.0",
    "body": [
        {
            "type": "TextBlock",
            "text": "Uživatel {{display_name}} zahájil hlasování."
        },
        {
            "type": "TextBlock",
            "text": "Předmět hlasování: {{poll_subject}}"
        },
        {
            "type": "TextBlock",
            "text": "Časový limit: {{time_limit}}"
        },
        {
            "type": "ActionSet",
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "Pro",
                    "id": "yes",
                    "style": "positive"
                },
                {
                    "type": "Action.Submit",
                    "title": "Proti",
                    "id": "no",
                    "style": "destructive"
                },
                {
                    "type": "Action.Submit",
                    "title": "Zdržuji se hlasování",
                    "id": "pass"
                }
            ],
            "id": "poll",
            "horizontalAlignment": "Center"
        }
    ],
    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json"
}

POLL_RESULTS_TEMPLATE = {
    "type": "AdaptiveCard",
    "version": "1.0",
    "body": [
        {
            "type": "TextBlock",
            "text": "Výsledky hlasování",
            "weight": "Bolder",
            "horizontalAlignment": "Center"
        },
        {
            "type": "ColumnSet",
            "columns": [
                {
                    "type": "Column",
                    "width": "stretch",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "Pro",
                            "horizontalAlignment": "Left",
                            "weight": "Bolder",
                            "color": "Good"
                        }
                    ]
                },
                {
                    "type": "Column",
                    "width": "stretch",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "Proti",
                            "horizontalAlignment": "Left",
                            "weight": "Bolder",
                            "color": "Warning"
                        }
                    ]
                },
                {
                    "type": "Column",
                    "width": "stretch",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "Zdržel se",
                            "horizontalAlignment": "Left",
                            "weight": "Bolder",
                            "color": "Dark"
                        }
                    ]
                }
            ]
        },
        {
            "type": "ColumnSet",
            "columns": [
                {
                    "type": "Column",
                    "width": "stretch",
                    "items": [
                    ]
                },
                {
                    "type": "Column",
                    "width": "stretch",
                    "items": [
                    ]
                },
                {
                    "type": "Column",
                    "width": "stretch",
                    "items": [
                    ]
                }
            ]
        }
    ],
    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json"
}

PARTICIPANT_ITEM_TEMPLATE = {
    "type": "TextBlock",
    "text": "{{display_name}}"
}
