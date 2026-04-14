def validate_train_id(train_id: str) -> tuple[bool, str]:
    if not train_id or train_id.strip() == "":
        return False, "Номер поезда не может быть пустым"

    try:
        train_num = int(train_id)
        if train_num <= 0:
            return False, "Номер поезда должен быть положительным числом"
        return True, ""
    except ValueError:
        return False, "Номер поезда должен быть целым числом"