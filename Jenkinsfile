pipeline {
    agent any
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        stage('Unit Test') {
            steps {
                sh 'mkdir -p reports && python3 -m pytest tests/ --junitxml=reports/results.xml'
            }
            post {
                always {
                    junit testResults: 'reports/results.xml', allowEmptyResults: true
                }
            }
        }
        stage('Validate Kubernetes Manifests') {
            steps {
                // Minikube is not pinned in this repository. Kubeconform's maintained
                // current schema is used until the cluster version is pinned as well.
                sh '''#!/usr/bin/env bash
                    set -euo pipefail
                    for manifest in k8s/*.yaml; do
                        echo "Validating $manifest"
                        docker run --rm -i ghcr.io/yannh/kubeconform:v0.6.7 -strict -summary < "$manifest"
                    done
                '''
            }
        }
        stage('Build Docker Image') {
            steps {
                sh 'docker build -t chaospulse:${BUILD_NUMBER} .'
            }
        }
    }
}
