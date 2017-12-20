GettingEntityFailedError = lambda m1, m2, m3: Exception("Getting entity [%s] from endpoint [%s] failed due to [%s]." % (m1, m2, m3))

ResourceNotFoundError = lambda r: Exception("The mandatory resource [%s] is not found." % r)
AtLeastOneResourceError = lambda m, *s: Exception("At least one of the resources " + str(list(s)) + " need to be in place. The error is [%s]." % m)
AllResourcesError = lambda m, *s: Exception("All the following mandatory resources " + str(list(s)) + " have to be configured. The error is [%s]." % m)


