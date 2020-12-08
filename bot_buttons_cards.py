def wrap_form(form):
    card = EMPTY_CARD
    card["content"] = form
    
    return card

def nested_replace(structure, original, new):
    """replace {{original}} wrapped strings with new value
    use recursion to walk the whole sructure
    
    arguments:
    structure -- input dict / list / string
    original -- string to search for
    new -- will replace every occurence of {{original}}
    """
    if type(structure) == list:
        return [nested_replace( item, original, new) for item in structure]

    if type(structure) == dict:
        return {key : nested_replace(value, original, new)
                     for key, value in structure.items() }

    if type(structure) == str:
        return structure.replace("{{"+original+"}}", str(new))
    else:
        return structure
        
EMPTY_CARD = {
    "contentType": "application/vnd.microsoft.card.adaptive",
    "content": None,
}

DEFAULT_FORM_MSG = "Toto je formulář. Zobrazíte si ho ve webovém klientovi Webex Teams nebo v desktopové aplikaci."

DEFAULT_TIME_LIMIT = "20"

YEA_STYLE = "good"
NAY_STYLE = "warning"
ABSTAIN_STYLE = "emphasis"

WELCOME_TEMPLATE = {
    "type": "AdaptiveCard",
    "version": "1.0",
    "body": [
        {
            "type": "TextBlock",
            "text": "Vítá vás bot pro řízení hlasování",
            "horizontalAlignment": "Center",
            "weight": "Bolder",
            "size": "Medium"
        },
        {
            "type": "TextBlock",
            "text": "Zahajte prosím novou schůzi"
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
                                "type": "ColumnSet",
                                "columns": [
                                    {
                                        "type": "Column",
                                        "width": "stretch",
                                        "items": [
                                            {
                                                "type": "TextBlock",
                                                "text": "Název schůze:",
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
                                                "placeholder": "Napište název",
                                                "id": "meeting_subject"
                                            }
                                        ]
                                    }
                                ]
                            },
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

START_POLL_BLOCK = [ {
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
                            "title": "10s",
                            "value": "10"
                        },
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
                    "value": "{{time_limit}}"
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
            "id": "poll_start",
            "data": {"action": "start_poll"}
        }
    ],
    "horizontalAlignment": "Right"
} ]

NEXT_POLL_BLOCK = {
    "type": "ActionSet",
    "horizontalAlignment": "Right",
    "actions": [
        {
            "type": "Action.ShowCard",
            "title": "Další hlasování",
            "card": {
                "type": "AdaptiveCard",
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "body": START_POLL_BLOCK
            },
            "id": "create_poll_card"
        }
    ],
    "id": "start_poll_set"
}

END_MEETING_BLOCK = {
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
                                "id": "end_meeting",
                                "data": {"action": "end_meeting"}
                            }
                        ]
                    }
                ]
            },
            "id": "end_meeting_card"
        }
    ],
    "id": "end_meeting_set"
}

START_MEETING_TEMPLATE = {
    "type": "AdaptiveCard",
    "version": "1.0",
    "body": [
        {
            "type": "TextBlock",
            "text": "Schůze \"{{meeting_subject}}\" zahájena",
            "horizontalAlignment": "Center",
            "weight": "Bolder",
            "size": "Medium"
        },
        {
            "type": "TextBlock",
            "text": "{{display_name}} zahájil schůzi."
        },
        {
            "type": "RichTextBlock",
            "inlines": [
                {
                    "type": "TextRun",
                    "text": "Klikněte na tlačítko "
                },
                {
                    "type": "TextRun",
                    "text": "Přítomen",
                    "weight": "Bolder"
                },
                {
                    "type": "TextRun",
                    "text": ". Jinak bude vaše přítomnost zaznamenána až od chvíle, kdy se aktivně zúčastníte hlasování."
                }
            ]
        },
        {
            "type": "ActionSet",
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "Přítomen",
                    "id": "present",
                    "data": {"action": "present"}
                }
            ],
            "horizontalAlignment": "Right",
            "id": "presence_indication"
        },
        {
            "type": "ActionSet",
            "horizontalAlignment": "Right",
            "actions": [
                {
                    "type": "Action.ShowCard",
                    "title": "Hlasování",
                    "card": {
                        "type": "AdaptiveCard",
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "body": nested_replace(START_POLL_BLOCK, "time_limit", DEFAULT_TIME_LIMIT)
                    },
                    "id": "create_poll_card"
                }
            ],
            "id": "start_poll_set"
        },
        {
            "type": "ActionSet",
            "horizontalAlignment": "Right",
            "actions": [
                {
                    "type": "Action.ShowCard",
                    "title": "Ukončit hlasování",
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
                                        "id": "end_poll",
                                        "data": {"action": "end_poll"}
                                    }
                                ]
                            }
                        ]
                    },
                    "id": "end_poll_card"
                }
            ],
            "id": "end_poll_set"
        },
        END_MEETING_BLOCK
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
            "type": "TextBlock",
            "text": "{{display_name}} ukončil schůzi."
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
                                "type": "ColumnSet",
                                "columns": [
                                    {
                                        "type": "Column",
                                        "width": "stretch",
                                        "items": [
                                            {
                                                "type": "TextBlock",
                                                "text": "Název schůze:",
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
                                                "placeholder": "Napište název",
                                                "id": "meeting_subject"
                                            }
                                        ]
                                    }
                                ]
                            },
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
            "text": "{{display_name}} zahájil hlasování."
        },
        {
            "type": "RichTextBlock",
            "inlines": [
                {
                    "type": "TextRun",
                    "text": "Téma hlasování: "
                },
                {
                    "type": "TextRun",
                    "text": "{{poll_subject}}",
                    "weight": "Bolder"
                },
            ]
        },
        {
            "type": "TextBlock",
            "text": "Časový limit: {{time_limit}}s"
        },
        {
            "type": "ActionSet",
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "Pro",
                    "id": "yea",
                    "style": "positive",
                    "data": {"vote": "yea"}
                },
                {
                    "type": "Action.Submit",
                    "title": "Proti",
                    "id": "nay",
                    "style": "destructive",
                    "data": {"vote": "nay"}
                },
                {
                    "type": "Action.Submit",
                    "title": "Zdržuji se",
                    "id": "abstain",
                    "data": {"vote": "abstain"}
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
            "text": "{{poll_subject}} - výsledky hlasování",
            "weight": "Bolder",
            "horizontalAlignment": "Center"
        },
        {
            "type": "ColumnSet",
            "style": "attention",
            "columns": [
                {
                    "type": "Column",
                    "width": "stretch",
                    # "style": YEA_STYLE,
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "Pro ({{yea_count}})",
                            "horizontalAlignment": "Left",
                            "weight": "Bolder",
                            "color": "Good"
                        }
                    ]
                },
                {
                    "type": "Column",
                    "width": "stretch",
                    # "style": NAY_STYLE,
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "Proti ({{nay_count}})",
                            "horizontalAlignment": "Left",
                            "weight": "Bolder",
                            "color": "Warning"
                        }
                    ]
                },
                {
                    "type": "Column",
                    "width": "stretch",
                    # "style": ABSTAIN_STYLE,
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "Zdržel se ({{abstain_count}})",
                            "horizontalAlignment": "Left",
                            "weight": "Bolder",
                            "color": "Dark"
                        }
                    ]
                }
            ]
        }
    ],
    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json"
}

RESULT_PARTICIPANT_TEMPLATE = {
    "type": "TextBlock",
    "text": "{{display_name}}",
    "horizontalAlignment": "Left",
}

PARTICIPANT_ITEM_TEMPLATE = {
    "type": "TextBlock",
    "text": "{{display_name}}"
}
