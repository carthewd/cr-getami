# CloudFormation Custom Resource to get AMIs

This is a lambda custom resource for CloudFormation to retrieve the latest AMI for a number OSes. Instead of maintaining maps of AMIs you can simply add the resource and define the OS in the function - i.e., no need to maintain mappings with AMI IDs. 

### Usage 
Full example template included

```yaml
  GetAmi:
    Type: Custom::GetAmi
    Properties:
      ServiceToken: !GetAtt GetAmiLambda.Arn
      OS: rhel7
      # log level
      loglevel: debug

Resources:
  MyEC2Instance:
    DependsOn: [ GetAmiLambda ]
    Type: AWS::EC2::Instance
    Properties:
      ImageId: !GetAtt GetAmi.AmiId
```

# Supported OSes
RHEL
Ubuntu
SLES
Windows
Amazon Linux
Amazon Linux 2
Official ECS AMIs
