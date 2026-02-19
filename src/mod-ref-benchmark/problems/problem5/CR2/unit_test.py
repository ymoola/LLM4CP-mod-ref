import traceback

def handle_assertions(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AssertionError as e:
            return ("fail", str(e))
        except Exception as e:
            return {
                "err": repr(str(e)),
                "err_trace": repr(''.join(traceback.format_exception(None, e, e.__traceback__)))
            }
    return wrapper


@handle_assertions
def cr2_verify_func(data_dict, hypothesis_solution):
    try:
        digits = hypothesis_solution["digits"]
    except Exception as e:
        return f"solFormatError: {str(e)}"

    # Must have 9 digits
    assert len(digits) == 9, "digits must have length 9"

    # All must be integers 1..9
    for d in digits:
        assert isinstance(d, int) and 1 <= d <= 9, "digits must be between 1 and 9"

    # Distinctness
    assert len(set(digits)) == 9, "digits must be distinct"

    a, b, c, d, e, f, g, h, i = digits

    BC = 10*b + c
    EF = 10*e + f
    HI = 10*h + i

    # CR2 check: strict ascending denominators
    assert BC < EF < HI, "Denominators are not strictly increasing (BC < EF < HI)"

    # Original equality check
    lhs = a*EF*HI + d*BC*HI + g*BC*EF
    rhs = BC*EF*HI
    assert lhs == rhs, "Original arithmetic constraint is violated"

    return "pass"