
def convert_to_ordinal(number):
    """
    Converts a number to its ordinal form.
    """
    if number % 100 // 10 == 1:
        return '%dth' % number
    elif number % 10 == 1:
        return '%dst' % number
    elif number % 10 == 2:
        return '%dnd' % number
    elif number % 10 == 3:
        return '%drd' % number
    else:
        return '%dth' % number