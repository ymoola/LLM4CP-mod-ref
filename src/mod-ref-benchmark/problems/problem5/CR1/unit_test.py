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
    # Extract
    try:
        digits = hypothesis_solution["digits"]
    except:
        return "solFormatError: missing digits"

    # 1. Length check
    assert len(digits) == 9, "digits must have length 9"

    # 2. Domain check
    for d in digits:
        assert 1 <= d <= 9, f"Digit {d} is outside 1..9"

    # 3. Distinctness
    assert len(set(digits)) == 9, "Digits must be all distinct"

    # 4. Check all 6 permutations satisfy equation
    import itertools

    a,b,c,d,e,f,g,h,i = digits
    num = [a, d, g]
    den = [10*b + c, 10*e + f, 10*h + i]

    for perm in itertools.permutations([0,1,2]):
        lhs = num[perm[0]]*den[perm[1]]*den[perm[2]] + \
              num[perm[1]]*den[perm[0]]*den[perm[2]] + \
              num[perm[2]]*den[perm[0]]*den[perm[1]]
        rhs = den[0] * den[1] * den[2]

        assert lhs == rhs, f"Permutation {perm} does not satisfy the equality"

    return "pass"