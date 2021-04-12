import localization_strings as ls

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
        
def nested_replace_dict(structure, replace_dict):
    for (key, value) in replace_dict.items():
        structure = nested_replace(structure, key, value)
        
    return structure
    
def localize(structure, language):
    if not language in ls.LOCALES.keys():
        return structure
        
    lang_dict = ls.LOCALES[language]
    return nested_replace_dict(structure, lang_dict)
        
EMPTY_CARD = {
    "contentType": "application/vnd.microsoft.card.adaptive",
    "content": None,
}

DEFAULT_FORM_MSG = "{{loc_default_form_msg}}"

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
            "text": "{{loc_bot_welcome_1}}",
            "horizontalAlignment": "Center",
            "weight": "Bolder",
            "size": "Medium"
        },
        {
            "type": "TextBlock",
            "text": "{{loc_bot_welcome_2}}"
        },
        {
            "type": "ActionSet",
            "horizontalAlignment": "Right",
            "actions": [
                {
                    "type": "Action.ShowCard",
                    "title": "{{loc_bot_welcome_3}}",
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
                                                "text": "{{loc_bot_welcome_4}}:",
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
                                                "placeholder": "{{loc_bot_welcome_5}}",
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
                                        "title": "{{loc_bot_welcome_6}}",
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

TIME_LIMITS = [
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
        "title": "1 {{loc_poll_block_5}}",
        "value": "60"
    },
    {
        "title": "2 {{loc_poll_block_6}}",
        "value": "120"
    }
]

START_POLL_BLOCK = [ {
    "type": "TextBlock",
    "text": "{{loc_poll_block_1}}",
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
                    "text": "{{loc_poll_block_2}}:",
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
                    "placeholder": "{{loc_poll_block_3}}",
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
                    "text": "{{loc_poll_block_4}}:",
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
                    "placeholder": "{{loc_poll_block_8}}",
                    "choices": TIME_LIMITS,
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
            "title": "{{loc_poll_block_7}}",
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
            "title": "{{loc_next_poll_block_1}}",
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
            "title": "{{loc_end_meeting_block_1}}",
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
                                "title": "{{loc_end_meeting_block_2}}",
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
            "text": "{{loc_start_meeting_1}} \"{{meeting_subject}}\" {{loc_start_meeting_2}}",
            "horizontalAlignment": "Center",
            "weight": "Bolder",
            "size": "Medium"
        },
        {
            "type": "TextBlock",
            "text": "{{display_name}} {{loc_start_meeting_3}}."
        },
        {
            "type": "RichTextBlock",
            "inlines": [
                {
                    "type": "TextRun",
                    "text": "{{loc_start_meeting_4}} "
                },
                {
                    "type": "TextRun",
                    "text": "{{loc_start_meeting_5}}",
                    "weight": "Bolder"
                },
                {
                    "type": "TextRun",
                    "text": " {{loc_start_meeting_6}}."
                }
            ]
        },
        {
            "type": "ActionSet",
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "{{loc_start_meeting_7}}",
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
                    "title": "{{loc_start_meeting_8}}",
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
                    "title": "{{loc_start_meeting_9}}",
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
                                        "title": "{{loc_start_meeting_10}}",
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
            "text": "{{loc_end_meeting_1}}",
            "horizontalAlignment": "Center",
            "weight": "Bolder",
            "size": "Medium"
        },
        {
            "type": "TextBlock",
            "text": "{{display_name}} {{loc_end_meeting_2}}."
        },
        {
            "type": "ActionSet",
            "horizontalAlignment": "Right",
            "actions": [
                {
                    "type": "Action.ShowCard",
                    "title": "{{loc_end_meeting_3}}",
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
                                                "text": "{{loc_end_meeting_4}}:",
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
                                                "placeholder": "{{loc_end_meeting_5}}",
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
                                        "title": "{{loc_end_meeting_6}}",
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
                            "text": "{{loc_submit_poll_1}}:",
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
                            "placeholder": "{{loc_submit_poll_2}}",
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
                            "text": "{{loc_submit_poll_3}}:",
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
                            "placeholder": "{{loc_submit_poll_7}}",
                            "choices": TIME_LIMITS,
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
                    "title": "{{loc_submit_poll_4}}",
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
                    "title": "{{loc_submit_poll_5}}",
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
                                        "title": "{{loc_submit_poll_6}}",
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
            "text": "{{display_name}} {{loc_poll_template_1}}."
        },
        {
            "type": "RichTextBlock",
            "inlines": [
                {
                    "type": "TextRun",
                    "text": "{{loc_poll_template_2}}: "
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
            "text": "{{loc_poll_template_3}}: {{time_limit}}s"
        },
        {
            "type": "ActionSet",
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "{{loc_poll_template_4}}",
                    "id": "yea",
                    "style": "positive",
                    "data": {"vote": "yea"}
                },
                {
                    "type": "Action.Submit",
                    "title": "{{loc_poll_template_5}}",
                    "id": "nay",
                    "style": "destructive",
                    "data": {"vote": "nay"}
                },
                {
                    "type": "Action.Submit",
                    "title": "{{loc_poll_template_6}}",
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
            "text": "{{poll_subject}} - {{loc_poll_results_1}}",
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
                            "text": "{{loc_poll_results_2}} ({{yea_count}})",
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
                            "text": "{{loc_poll_results_3}} ({{nay_count}})",
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
                            "text": "{{loc_poll_results_4}} ({{abstain_count}})",
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

SETTINGS_BLOCK = [
    {
        "type": "ColumnSet",
        "columns": [
            {
                "type": "Column",
                "width": "stretch",
                "items": [
                    {
                        "type": "TextBlock",
                        "text": "{{loc_settings_block_1}}",
                        "wrap": True
                    }
                ]
            },
            {
                "type": "Column",
                "width": "stretch",
                "items": [
                    {
                        "type": "Input.ChoiceSet",
                        "choices": ls.lang_list_for_card(),
                        "placeholder": "{{loc_settings_block_2}}",
                        "id": "language",
                        "value": "en_US"
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
                        "text": "{{loc_settings_block_3}}",
                        "wrap": True
                    }
                ]
            },
            {
                "type": "Column",
                "width": "stretch",
                "items": [
                    {
                        "type": "Input.ChoiceSet",
                        "choices": [
                            {
                                "title": "{{loc_settings_block_4}}",
                                "value": "yes"
                            },
                            {
                                "title": "{{loc_settings_block_5}}",
                                "value": "no"
                            }
                        ],
                        "placeholder": "",
                        "style": "expanded",
                        "id": "partial_results",
                        "value": "no"
                    }
                ]
            }
        ]
    }
]

USER_SETTINGS_TEMPLATE = {
    "type": "AdaptiveCard",
    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
    "version": "1.0",
    "body": [
        {
            "type": "TextBlock",
            "text": "{{loc_user_settings_1}}",
            "wrap": True,
            "weight": "Bolder"
        },
        {
            "type": "TextBlock",
            "text": "{{loc_user_settings_2}}",
            "wrap": True
        }
    ] + SETTINGS_BLOCK,
    "actions": [
        {
            "type": "Action.Submit",
            "title": "{{loc_user_settings_3}}"
        }
    ]
}

ROOM_SETTINGS_TEMPLATE = {
    "type": "AdaptiveCard",
    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
    "version": "1.0",
    "body": [
        {
            "type": "TextBlock",
            "text": "{{loc_room_settings_1}}",
            "wrap": True,
            "weight": "Bolder"
        },
        {
            "type": "TextBlock",
            "text": "{{loc_room_settings_2}}",
            "wrap": True
        }
    ] + SETTINGS_BLOCK,
    "actions": [
        {
            "type": "Action.Submit",
            "title": "{{loc_room_settings_3}}"
        }
    ]
}
