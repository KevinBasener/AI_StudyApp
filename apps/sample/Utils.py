import json


def extract_and_parse_json(input_obj):
    print("Start json extract ------------")
    print("Input Obj: ", input_obj)

    # Überprüfen, ob das input_obj ein stringähnliches Objekt oder direkt konvertierbar ist
    if hasattr(input_obj, "value"):
        input_str = input_obj.value
    elif isinstance(input_obj, str):
        input_str = input_obj
    else:
        try:
            input_str = str(
                input_obj
            )  # Versuchen, das Objekt in einen String zu konvertieren
        except Exception as e:
            print(f"Fehler beim Konvertieren des Input Objekts in einen String: {e}")
            return None, f"Fehler beim Konvertieren des Input Objekts: {e}"

    print("InputString: ", input_str)
    # Versuchen Sie zuerst, den Standardfall mit ```json zu finden
    start_marker = "```json"
    end_marker = "```"
    start_index = input_str.find(start_marker)
    print("Startindex: " + str(start_index))

    if start_index == -1:
        print("Standardfall nicht gefunden.")
        # Wenn kein ```json gefunden wurde, suchen Sie nach dem Beginn eines JSON-Arrays oder Objekts
        start_index = input_str.find("[")
        start_marker = "["
        end_marker = "\n```" if input_str.find("\n```", start_index) != -1 else "]"

    end_index = (
        input_str.find(end_marker, start_index + 1) if end_marker else len(input_str)
    )

    if start_index == -1:
        print("Standardfall 2 mit [] nicht gefunden.")
        # Wenn kein ```json gefunden wurde, suchen Sie nach dem Beginn eines JSON-Arrays oder Objekts
        start_index = input_str.find("{")
        start_marker = "{"
        end_marker = "\n```" if input_str.find("\n```", start_index) != -1 else "}"

    end_index = (
        input_str.find(end_marker, start_index + 1) if end_marker else len(input_str)
    )
    if start_index != -1 and end_index != -1:
        # Extrahieren des JSON-Teils
        if len(start_marker) > 1:
            start_index += len(start_marker)
        else:
            start_index += -1
            end_index += 1
        json_str = input_str[start_index:end_index].strip()
        print("Startindex: " + str(start_index))
        print("Endindex: " + str(end_index))
        print("JSON-Teil:", json_str)

        # Entfernen von möglichen ``` am Ende, falls wir ohne end_marker sind
        if not end_marker:
            json_str = json_str.rstrip("`")

        # Parsen des JSON-Strings
        try:
            print("JSON-String:", json_str)
            json_data = json.loads(json_str)
            print("JSON-Daten:", json_data)
            return json_data, None
        except json.JSONDecodeError as e:
            print(f"Fehler beim Parsen des JSON-Strings: {e}")
            return (
                None,
                "Fehler beim Parsen des JSON-Strings. Oft hilft eine neue Anfrage mit dem Aufruf nach neuer Formatierung: "
                + str(e),
            )
    else:
        print("JSON-Teil nicht gefunden.")
        return None, "JSON-Teil nicht gefunden." + input_str
