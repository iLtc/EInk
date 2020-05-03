<?php
   if ($_GET['token'] != 'oi0zA1d7pZEztNAb5AXg')
      exit();
      
   require 'vendor/autoload.php';
   
   use Aws\S3\S3Client;
   use Aws\Exception\AwsException;
   
   include 'config.php';

   $s3 = new Aws\S3\S3Client([
      'version' => 'latest',
      'region' => 'us-east-1',
      'credentials' => [
            'key'    => $aws_key,
            'secret' => $aws_secret,
       ],
   ]);
   
   $cmd = $s3->getCommand('GetObject', [
      'Bucket' => 'iltc-eink',
      'Key' => 'main/' . $_GET['file']
   ]);
   
   $request = $s3->createPresignedRequest($cmd, '+5 minutes');
   
   $presignedUrl = (string)$request->getUri();
   
   header('Location: ' . $presignedUrl);