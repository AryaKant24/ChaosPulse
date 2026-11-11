pipeline {
    agent any
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        stage('Lint & Unit Test') {
            steps {
                sh 'python3 -m pytest tests/ --junitxml=reports/results.xml'
            }
            post {
                always {
                    junit 'reports/results.xml'
                }
            }
        }
        stage('Build Docker Image') {
            steps {
                sh 'docker build -t chaospulse:${BUILD_NUMBER} .'
            }
        }
    }
}