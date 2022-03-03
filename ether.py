def kwei(wei):
    return int(wei)*pow(10,-3)
    #return int(wei)*pow(10,-3)

def mwei(wei):
    return kwei(int(wei))*pow(10,-3)
    #return int(wei)*pow(10,-6)

def gwei(wei):
    return mwei(int(wei))*pow(10,-3)
    #return int(wei)*pow(10,-9)

def szabo(wei):
    return gwei(int(wei))*pow(10,-3)
    #return int(wei)*pow(10,-12)

def finney(wei):
    return szabo(int(wei))*pow(10,-3)
    #return int(wei)*pow(10,-15)

def ether(wei):
    return finney(int(wei))*pow(10,-3)
    #return int(wei)*pow(10,-18)

def kwei2wei(kwei):
    return float(kwei)*pow(10, 3)

def mwei2wei(mwei):
    return float(mwei)*pow(10, 6)

def gwei2wei(gwei):
    return float(gwei)*pow(10, 9)

def szabo2wei(szabo):
    return float(szabo)*pow(10, 12)

def finney2wei(finney):
    return float(finney)*pow(10, 15)

def ether2wei(ether):
    return float(ether)*pow(10, 18)
