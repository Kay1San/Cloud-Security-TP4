# TP4 - Infrastructure as Code Security

Ce repertoire contient le code Boto3 pour configurer une infrastructure AWS.

L'architecture de ce répertoire est telle que : 
* Boto3 : Contient deux fichiers (constamment mises à jour en fonction des questions) sur la configuration du VPC ainsi que du bucket S3
* CloudFormation : Contient les fichiers .yaml et .json utilisés lors des étapes préalables pour configurer l'architecture AWS
* Trivy-Outputs: Contient l'architecture .yaml du code Boto3 (obtenu par Former2) ainsi que les fichiers de Scans de Trivy
* Figures: Contient les captures de déploiement

## Installation
1. Installer les dépendences via pip install -r requirements.txt
2. Configurer un fichier variable .env contenant les éléments suivants:
   * aws_access_key
   * aws_secret_access_key
   * aws_session_token (seulement si AWS learner lab est utilisé. Commenter les lignes du code Boto3 faisant référence à cette session si AWS Learner Lab n'est pas utilisé)
   * kms_key_arn
   * bucket_arn
   * KEY_NAME
   * ROLE_ARN
