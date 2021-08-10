# ccs - CLI for CloudSigma API

**CCS** is a command line interface for the CloudSigma API.

It implements a set of commands with arguments and options representing the functionality
of the excellent pycloudsigma module.

The purpose is to facilitate ad-hoc and scripted management of cloudsigma resources.


## Credentials 

CloudSigma account credentials may be provided as command line options.
If not provided, they are read from the environment variables shown in the `--help` output.
Command line options have precedence over environment values.

#### Each call returns a JSON structure with the format:
```
{
  "status": STATUS_BOOL,
  "result": ITEM_STRUCT
}
```
#### Where:
Value	      | Description
------------- | ----------------------------------------------------------
STATUS_BOOL   | True if the call succeeded, or False to indicate a failure
RESULT_STRUCT | API call return data, or an error message in case of failure


## ENVIRONMENT

#### Required
```
CCS_USERNAME=user@example.com
CCS_PASSWORD=XXXXXXXXXXXXXXX
CCS_REGION=sjc
```

## References
https://docs.cloudsigma.com/en/2.14.3/
https://github.com/cloudsigma/pycloudsigma
