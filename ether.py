def kwei(wei):
    return int(wei)/1000

def mwei(wei):
    return kwei(int(wei))/1000

def gwei(wei):
    return mwei(int(wei))/1000

def szabo(wei):
    return gwei(int(wei))/1000

def finney(wei):
    return szabo(int(wei))/1000

def ether(wei):
    return finney(int(wei))/1000
