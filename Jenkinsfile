#!/usr/bin/env groovy
pipeline {
   environment {
       FEATURE_NAME = BRANCH_NAME.replaceAll('[\\(\\)_/]','-').toLowerCase()
       NEXUS_USERNAME = credentials('NEXUS_USERNAME')
       NEXUS_PASSWORD = credentials('NEXUS_PASSWORD')
       HTTP_PROXY = "http://bh-app-proxy.corp.dmz:8080"
       HTTPS_PROXY = "http://bh-app-proxy.corp.dmz:8080"
   }
   agent any
   triggers {
       cron(env.BRANCH_NAME == 'master' ? 'H H * * 1-5' : '')
   }
   stages {
        stage('Build & Push Image') {
            steps {
                sh 'make nexusLogin dockerBuild dockerPush'
            }
        }

        stage('Docker Scan') {
            steps {
                sh "make dockerScan"
            }
            post {
                cleanup {
                    sh "docker-compose down -v"
                }
            }
        }

        stage('Push Latest Tag') {
            when { branch 'master' }
            steps {
                sh 'make nexusLogin dockerPushLatest'
            }
        }
    }


}
