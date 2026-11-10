pipeline {
  agent any

  options { disableConcurrentBuilds() }

  triggers { githubPush() }

  environment {
    ACR_NAME = 'sriramacr2026'              // <- your registry name
    ACR      = 'sriramacr2026.azurecr.io'   // <- your registry name
    RG       = 'rg-app-dev'
    APP      = 'auth-service'               // Container App name = image name
  }

  stages {
    stage('Version') {
      steps {
        script {
          env.TAG = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
          echo "Version tag: ${env.TAG}"
        }
      }
    }

    stage('Test') {
      steps {
        // Builds the 'test' stage of the Dockerfile, which runs pytest.
        sh 'docker build --pull --target test -t ${APP}-test:${TAG} .'
      }
    }

    stage('Build & push image') {
      steps {
        sh 'az login --identity --output none'
        sh 'az extension add -n containerapp --upgrade --only-show-errors'
        sh 'az acr login -n $ACR_NAME'
        sh 'docker build --target runtime -t ${ACR}/${APP}:${TAG} .'
        sh 'docker push ${ACR}/${APP}:${TAG}'
      }
    }

    stage('Deploy to Azure') {
      steps {
        sh 'az containerapp update -n ${APP} -g ${RG} --image ${ACR}/${APP}:${TAG} --output none'
        echo "Deployed ${APP}:${TAG}"
      }
    }
  }

  post {
    always { sh 'docker image prune -f || true' }
  }
}
