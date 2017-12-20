IN_SPLUNK_ENV = True
try:
    import splunk.util as splunk_util
except ImportError:
    IN_SPLUNK_ENV = False

def _normalizeBoolean(input, enableStrictMode, includeIntegers):
    trueThings = ['true', 't', 'on', 'yes', 'y']
    falseThings = ['false', 'f', 'off', 'no', 'n']

    if includeIntegers:
        trueThings.append('1')
        falseThings.append('0')

    def norm(input):
        if input == True: return True
        if input == False: return False

        try:
            test = input.strip().lower()
        except:
            return input

        if test in trueThings:
            return True
        elif test in falseThings:
            return False
        elif enableStrictMode:
            raise ValueError, 'Unable to cast value to boolean: %s' % input
        else:
            return input

    if isinstance(input, dict):
        for k,v in input.items():
            input[k] = norm(v)
        return input
    else:
        return norm(input)
            
def normalizeBoolean(input, enableStrictMode=False, includeIntegers=True):
    bool_value = False
    if IN_SPLUNK_ENV:
        bool_value = splunk_util.normalizeBoolean(input, enableStrictMode, includeIntegers)
    else:
        bool_value = _normalizeBoolean(input, enableStrictMode, includeIntegers)
    return bool_value
        
