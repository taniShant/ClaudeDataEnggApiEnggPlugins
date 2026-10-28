# Build Command Reference: Complete Guide

## Executive Summary

Complete reference for building, testing, and deploying MCA2 EPS applications. Includes Gradle commands, Maven equivalents, CI/CD configuration, and deployment instructions.

---

## GRADLE BUILD COMMANDS

### Basic Build Operations

```bash
# Full build with all tests
./gradlew build

# Build without tests (fast)
./gradlew build -x test -x integrationTest

# Clean build directory
./gradlew clean

# Clean and build
./gradlew clean build

# Display build version
./gradlew --version

# Parallel build (faster on multi-core)
./gradlew build --parallel
```

### Building Specific Modules

```bash
# Build single module (mca-context)
./gradlew :mca-libraries:mca-context:build

# Build multiple modules
./gradlew :mca-libraries:mca-context:build :mca-libraries:mca-filter-core:build

# Build all library modules
./gradlew :mca-libraries:*:build

# Build all extension modules
./gradlew :mca-extension-libraries:*:build

# Build specific example app
./gradlew :mca-examples:mca-experience-api-cardcontrol-reference-app:build
```

### Incremental vs Full Builds

```bash
# Incremental build (only changed modules)
./gradlew build

# Force full build (ignore cache)
./gradlew build --no-build-cache

# Refresh build dependencies
./gradlew build --refresh-dependencies
```

---

## TESTING COMMANDS

### Unit Testing

```bash
# Run all unit tests
./gradlew test

# Run unit tests for single module
./gradlew :mca-libraries:mca-context:test

# Run single test class
./gradlew :mca-libraries:mca-context:test --tests com.barclays.global.mca.context.ContextTest

# Run single test method
./gradlew :mca-libraries:mca-context:test --tests com.barclays.global.mca.context.ContextTest.testContextCreation

# Run test with pattern matching
./gradlew test --tests *Filter*

# Run tests matching regex
./gradlew test --tests ".*Context.*"

# Run tests in parallel
./gradlew test --parallel

# Run tests with verbose output
./gradlew test -i

# Run tests with full stack traces
./gradlew test --full-stacktrace
```

### Integration Testing

```bash
# Run integration tests only
./gradlew integrationTest

# Run integration tests for specific module
./gradlew :mca-examples:mca-experience-api-cardcontrol-reference-app:integrationTest

# Run integration test class
./gradlew integrationTest --tests com.barclays.global.mca.integration.FilterChainIntegrationTest

# Run single integration test method
./gradlew integrationTest --tests com.barclays.global.mca.integration.FilterChainIntegrationTest.testContextFilterPropagation
```

### Code Coverage (JaCoCo)

```bash
# Generate code coverage report
./gradlew jacocoTestReport

# Generate coverage for specific module
./gradlew :mca-libraries:mca-context:jacocoTestReport

# Check coverage thresholds (100% incremental)
./gradlew check

# View coverage report
./gradlew jacocoTestReport && open build/reports/jacoco/test/html/index.html

# Generate coverage for integration tests
./gradlew jacocoIntegrationTestReport
```

### Code Quality Analysis

```bash
# Run Checkstyle across all modules
./gradlew allCheckstyle

# Run Checkstyle for specific module
./gradlew :mca-libraries:mca-context:checkstyleMain

# Run Sonar analysis
./gradlew sonarqube -Dsonar.login=${SONAR_TOKEN}

# Run Mutation Testing (PiTest)
./gradlew :mca-libraries:mca-context:pitest -PpitestTargetClasses=com.barclays.global.mca.context.IOLSchema

# Run SpotBugs (static analysis)
./gradlew spotbugsMain spotbugsTest
```

---

## GRADLE PROPERTIES & FLAGS

### Performance Optimization

```bash
# Enable daemon (faster subsequent builds)
./gradlew --daemon build

# Stop daemon
./gradlew --stop

# Run with 4 parallel threads
./gradlew build -P org.gradle.parallel=true -P org.gradle.parallel.threads=4

# Enable build cache
./gradlew build --build-cache

# Show build timing
./gradlew build --profile

# View profile report
./gradlew build --profile && open build/reports/profile/profile-*.html
```

### Dependency Management

```bash
# Show dependency tree
./gradlew dependencies

# Show dependency tree for specific module
./gradlew :mca-libraries:mca-context:dependencies

# Show compile-only dependencies
./gradlew dependencyInsight --dependency mca-context

# Check for outdated dependencies
./gradlew dependencyUpdates

# Generate dependency report
./gradlew generateDependencyReport
```

### Build Configuration

```bash
# Override property
./gradlew build -P propertyName=value

# Show all gradle properties
./gradlew properties

# Show available tasks
./gradlew tasks

# Show all tasks (including private)
./gradlew tasks --all

# Show init scripts
./gradlew init
```

---

## SPRING BOOT APPLICATION COMMANDS

### Local Development

```bash
# Run application with Gradle bootRun
./gradlew :mca-examples:mca-experience-api-cardcontrol-reference-app:bootRun

# Run with active profile
./gradlew bootRun --args='--spring.profiles.active=dev'

# Run with property override
./gradlew bootRun --args='--server.port=9080'

# Run with debugging
./gradlew bootRun --debug-jvm

# Run with custom JVM arguments
./gradlew bootRun --args='-Xmx2g -Xms2g'

# Build executable JAR
./gradlew bootJar

# Build thin JAR (without embedded container)
./gradlew build -P thin-jar
```

### Jar Packaging

```bash
# Build application JAR
./gradlew :mca-examples:mca-experience-api-cardcontrol-reference-app:bootJar

# Build with specific output name
./gradlew bootJar -P jarFileName=myapp-1.0.jar

# Build and run JAR
java -jar build/libs/cardcontrol-reference-app.jar

# Run JAR with properties
java -jar build/libs/app.jar --server.port=9080 --spring.profiles.active=prod

# Run JAR with environment variables
SPRING_PROFILES_ACTIVE=prod java -jar build/libs/app.jar

# Run JAR with external properties file
java -jar build/libs/app.jar --spring.config.location=application-prod.properties
```

### Debugging & Monitoring

```bash
# Run with Java debugger on port 5005
java -agentlib:jdwp=transport=dt_socket,server=y,suspend=n,address=5005 \
  -jar build/libs/app.jar

# Run with JMX monitoring
java -Dcom.sun.management.jmxremote \
  -Dcom.sun.management.jmxremote.port=9010 \
  -Dcom.sun.management.jmxremote.authenticate=false \
  -Dcom.sun.management.jmxremote.ssl=false \
  -jar build/libs/app.jar

# Run with GC logging
java -XX:+PrintGCDetails -XX:+PrintGCDateStamps \
  -Xloggc:gc.log \
  -jar build/libs/app.jar

# Run with heap dump on OutOfMemoryError
java -XX:+HeapDumpOnOutOfMemoryError \
  -XX:HeapDumpPath=./heap-dumps/ \
  -jar build/libs/app.jar
```

---

## MAVEN EQUIVALENTS

### Maven Build Commands

```bash
# Build all (Maven equivalent)
mvn clean install

# Build without tests
mvn clean install -DskipTests

# Build specific module
mvn clean install -pl mca-libraries:mca-context

# Build multiple modules
mvn clean install -pl mca-libraries:mca-context,mca-libraries:mca-filter-core

# Build with dependencies
mvn clean install -DdownloadSources=true -DdownloadJavadocs=true

# Clean build
mvn clean

# Compile only
mvn compile

# Package application
mvn package
```

### Maven Testing

```bash
# Run all tests
mvn test

# Run single test class
mvn test -Dtest=ContextTest

# Run single test method
mvn test -Dtest=ContextTest#testContextCreation

# Run integration tests
mvn verify

# Skip tests
mvn install -DskipTests

# Run with coverage
mvn clean test jacoco:report
```

### Maven Properties

```bash
# Show dependency tree
mvn dependency:tree

# Show resolved plugins
mvn dependency:list

# Check outdated dependencies
mvn versions:display-dependency-updates

# Analyze dependencies
mvn dependency:analyze
```

---

## DOCKER BUILD & DEPLOYMENT

### Docker Build

```bash
# Build Docker image from Dockerfile
docker build -t mca-cardcontrol:2.3.0 .

# Build with build arguments
docker build -t mca-cardcontrol:2.3.0 \
  --build-arg JAR_FILE=build/libs/cardcontrol-reference-app.jar .

# Build multi-stage image
docker build -t mca-cardcontrol:latest \
  --target runtime .

# Build and tag for registry
docker build -t registry.example.com/mca-cardcontrol:2.3.0 .

# Push image to registry
docker push registry.example.com/mca-cardcontrol:2.3.0

# View image layers
docker history mca-cardcontrol:2.3.0

# Inspect image
docker inspect mca-cardcontrol:2.3.0
```

### Docker Run

```bash
# Run application in Docker
docker run -p 8080:8080 mca-cardcontrol:2.3.0

# Run with environment variables
docker run -p 8080:8080 \
  -e SPRING_PROFILES_ACTIVE=prod \
  -e SERVER_PORT=8080 \
  mca-cardcontrol:2.3.0

# Run with mounted config
docker run -p 8080:8080 \
  -v /path/to/application.properties:/app/config/application.properties:ro \
  mca-cardcontrol:2.3.0

# Run in background
docker run -d -p 8080:8080 --name cardcontrol mca-cardcontrol:2.3.0

# View logs
docker logs cardcontrol

# Execute command in container
docker exec cardcontrol curl http://localhost:8080/health

# Stop container
docker stop cardcontrol

# Remove container
docker rm cardcontrol
```

### Docker Compose

```yaml
version: '3.8'
services:
  app:
    image: mca-cardcontrol:2.3.0
    ports:
      - "8080:8080"
    environment:
      SPRING_PROFILES_ACTIVE: prod
      SPRING_DATASOURCE_URL: jdbc:postgresql://db:5432/mca_db
      SPRING_DATASOURCE_USERNAME: postgres
      SPRING_DATASOURCE_PASSWORD: ${DB_PASSWORD}
    depends_on:
      - db

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: mca_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - db-data:/var/lib/postgresql/data

volumes:
  db-data:
```

### Docker Compose Commands

```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down

# Remove volumes on stop
docker-compose down -v

# Rebuild images
docker-compose build --no-cache

# Execute command
docker-compose exec app curl http://localhost:8080/health
```

---

## KUBERNETES DEPLOYMENT

### kubectl Commands

```bash
# Apply configuration
kubectl apply -f deployment.yaml

# View deployments
kubectl get deployments

# View pods
kubectl get pods

# View pod logs
kubectl logs <pod-name>

# Port forward
kubectl port-forward svc/mca-cardcontrol 8080:8080

# Get pod details
kubectl describe pod <pod-name>

# Execute command in pod
kubectl exec -it <pod-name> -- /bin/bash

# Update image
kubectl set image deployment/mca-cardcontrol \
  mca-cardcontrol=registry.example.com/mca-cardcontrol:2.3.1

# Rollback deployment
kubectl rollout undo deployment/mca-cardcontrol

# View deployment history
kubectl rollout history deployment/mca-cardcontrol
```

### Kubernetes Deployment Example

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mca-cardcontrol
  labels:
    app: mca-cardcontrol
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mca-cardcontrol
  template:
    metadata:
      labels:
        app: mca-cardcontrol
    spec:
      containers:
      - name: mca-cardcontrol
        image: registry.example.com/mca-cardcontrol:2.3.0
        ports:
        - containerPort: 8080
        env:
        - name: SPRING_PROFILES_ACTIVE
          value: "prod"
        - name: SPRING_DATASOURCE_URL
          value: "jdbc:postgresql://postgres-svc:5432/mca_db"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/readiness
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
        resources:
          limits:
            cpu: 1000m
            memory: 1Gi
          requests:
            cpu: 500m
            memory: 512Mi
---
apiVersion: v1
kind: Service
metadata:
  name: mca-cardcontrol
spec:
  selector:
    app: mca-cardcontrol
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
  type: LoadBalancer
```

---

## CI/CD CONFIGURATION

### GitHub Actions

```yaml
name: Build and Deploy

on:
  push:
    branches: [ main, release/* ]
  pull_request:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3

    - name: Set up Java
      uses: actions/setup-java@v3
      with:
        java-version: '21'
        distribution: 'temurin'

    - name: Build with Gradle
      run: ./gradlew build --parallel

    - name: Run tests
      run: ./gradlew test integrationTest

    - name: Generate code coverage
      run: ./gradlew jacocoTestReport

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        files: ./build/reports/jacoco/test/jacocoTestReport.xml

    - name: SonarQube scan
      run: ./gradlew sonarqube -Dsonar.login=${{ secrets.SONAR_TOKEN }}

    - name: Build Docker image
      run: docker build -t mca-cardcontrol:${{ github.sha }} .

    - name: Push to registry
      run: |
        echo ${{ secrets.REGISTRY_PASSWORD }} | docker login -u ${{ secrets.REGISTRY_USER }} --password-stdin
        docker tag mca-cardcontrol:${{ github.sha }} registry.example.com/mca-cardcontrol:${{ github.sha }}
        docker push registry.example.com/mca-cardcontrol:${{ github.sha }}

    - name: Deploy to Kubernetes
      if: github.ref == 'refs/heads/main'
      run: |
        kubectl set image deployment/mca-cardcontrol \
          mca-cardcontrol=registry.example.com/mca-cardcontrol:${{ github.sha }}
```

### GitLab CI

```yaml
stages:
  - build
  - test
  - quality
  - package
  - deploy

variables:
  GRADLE_OPTS: "-Dorg.gradle.daemon=false"
  REGISTRY: "registry.example.com"

build:
  stage: build
  image: gradle:8.5-jdk21
  script:
    - ./gradlew build -x test --parallel
  artifacts:
    paths:
      - build/
    expire_in: 1 day

test:
  stage: test
  image: gradle:8.5-jdk21
  dependencies:
    - build
  script:
    - ./gradlew test integrationTest
  artifacts:
    reports:
      junit: build/test-results/**/*.xml
    paths:
      - build/reports/jacoco/

coverage:
  stage: quality
  image: gradle:8.5-jdk21
  dependencies:
    - test
  script:
    - ./gradlew jacocoTestReport
  artifacts:
    paths:
      - build/reports/jacoco/

sonar:
  stage: quality
  image: gradle:8.5-jdk21
  script:
    - ./gradlew sonarqube -Dsonar.login=${SONAR_TOKEN}
  only:
    - merge_requests

docker:
  stage: package
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
    - docker build -t $REGISTRY/mca-cardcontrol:$CI_COMMIT_SHA .
    - docker push $REGISTRY/mca-cardcontrol:$CI_COMMIT_SHA
    - docker tag $REGISTRY/mca-cardcontrol:$CI_COMMIT_SHA $REGISTRY/mca-cardcontrol:latest
    - docker push $REGISTRY/mca-cardcontrol:latest

deploy_prod:
  stage: deploy
  image: bitnami/kubectl:latest
  script:
    - kubectl config use-context production
    - kubectl set image deployment/mca-cardcontrol mca-cardcontrol=$REGISTRY/mca-cardcontrol:$CI_COMMIT_SHA
  only:
    - main
  environment:
    name: production
    kubernetes:
      namespace: production
```

### Jenkins Pipeline

```groovy
pipeline {
    agent any

    environment {
        REGISTRY = 'registry.example.com'
        JAVA_HOME = '/usr/lib/jvm/java-21-temurin'
    }

    stages {
        stage('Checkout') {
            steps {
                git 'https://github.com/barclays/mca-java-common.git'
            }
        }

        stage('Build') {
            steps {
                sh './gradlew clean build -x test --parallel'
            }
        }

        stage('Test') {
            steps {
                sh './gradlew test integrationTest'
            }
        }

        stage('Code Quality') {
            parallel {
                stage('Checkstyle') {
                    steps {
                        sh './gradlew allCheckstyle'
                    }
                }
                stage('Coverage') {
                    steps {
                        sh './gradlew jacocoTestReport'
                    }
                }
                stage('SonarQube') {
                    steps {
                        sh './gradlew sonarqube -Dsonar.login=${SONAR_TOKEN}'
                    }
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                sh 'docker build -t $REGISTRY/mca-cardcontrol:${BUILD_NUMBER} .'
            }
        }

        stage('Push to Registry') {
            steps {
                sh '''
                    docker login -u ${REGISTRY_USER} -p ${REGISTRY_PASSWORD} $REGISTRY
                    docker push $REGISTRY/mca-cardcontrol:${BUILD_NUMBER}
                    docker tag $REGISTRY/mca-cardcontrol:${BUILD_NUMBER} $REGISTRY/mca-cardcontrol:latest
                    docker push $REGISTRY/mca-cardcontrol:latest
                '''
            }
        }

        stage('Deploy to Staging') {
            steps {
                sh '''
                    kubectl config use-context staging
                    kubectl set image deployment/mca-cardcontrol mca-cardcontrol=$REGISTRY/mca-cardcontrol:${BUILD_NUMBER}
                '''
            }
        }

        stage('Deploy to Production') {
            when {
                branch 'main'
            }
            input {
                message "Deploy to production?"
            }
            steps {
                sh '''
                    kubectl config use-context production
                    kubectl set image deployment/mca-cardcontrol mca-cardcontrol=$REGISTRY/mca-cardcontrol:${BUILD_NUMBER}
                '''
            }
        }
    }

    post {
        always {
            junit 'build/test-results/**/*.xml'
            publishHTML([
                reportDir: 'build/reports/jacoco/test/html',
                reportFiles: 'index.html',
                reportName: 'Code Coverage'
            ])
        }
        failure {
            emailext(
                subject: 'Build Failed: ${PROJECT_NAME}',
                body: 'Build failed. Check ${BUILD_URL} for details.',
                to: '${DEFAULT_RECIPIENTS}'
            )
        }
    }
}
```

---

## VERSION MANAGEMENT

### Gradle Version Plugin

```bash
# Check for updates
./gradlew dependencyUpdates

# Display dependency updates report
./gradlew dependencyUpdates -Drevision=release
```

### Manual Version Updates

```bash
# Update Gradle wrapper
./gradlew wrapper --gradle-version=8.5

# Update module version in gradle.properties
# Edit gradle.properties: version = 2.3.0

# Update BOM version
# Edit mca-java-common-bom/build.gradle: version = '2.3.0'

# Tag release in Git
git tag -a v2.3.0 -m "Release version 2.3.0"
git push origin v2.3.0
```

---

## PERFORMANCE PROFILING

### Gradle Build Profiling

```bash
# Generate build profile
./gradlew build --profile

# View profile results
open build/reports/profile/profile-2024-02-26-10-15-30.html

# Detailed timing output
./gradlew build --debug 2>&1 | grep -E "Execute|Task|took"

# Identify slow tasks
./gradlew build --scan
```

### JVM Application Profiling

```bash
# Run with Java Flight Recorder
java -XX:+UnlockCommercialFeatures \
  -XX:+FlightRecorder \
  -XX:StartFlightRecording=delay=5s,duration=30s,filename=myapp.jfr \
  -jar build/libs/app.jar

# Analyze JFR recording
jfr print myapp.jfr

# CPU profiling with perf (Linux)
perf record -g java -jar build/libs/app.jar
perf report

# Memory profiling with JProfiler
java -agentpath:/path/to/jprofiler/bin/linux-x64/libjprofilerti.so=port=8849 \
  -jar build/libs/app.jar
```

---

## TROUBLESHOOTING BUILD ISSUES

### Common Build Problems

```bash
# Gradle daemon not responding
./gradlew --stop
./gradlew build

# Out of memory during build
export GRADLE_OPTS="-Xmx4g"
./gradlew build

# Clean corrupted cache
rm -rf ~/.gradle/caches
./gradlew build

# Force dependency resolution
./gradlew build --refresh-dependencies

# Check for dependency conflicts
./gradlew dependencyInsight --dependency org.springframework.boot

# Verbose logging
./gradlew build -i --full-stacktrace

# Debug mode
./gradlew build -d
```

### Test Failures

```bash
# Run failing test with verbose output
./gradlew test -i --full-stacktrace

# Run single test
./gradlew test --tests com.barclays.global.mca.context.ContextTest

# Run test with system properties
./gradlew test -Dtest.env=local

# Check test timings
./gradlew test --profile

# View test report
./gradlew test && open build/reports/tests/test/index.html
```

---

## DEPLOYMENT CHECKLIST

Before deploying to production:

```
✓ All tests passing (unit + integration)
✓ Code coverage ≥ 100% incremental
✓ Sonar scan: no blocker/critical/major issues
✓ Veracode scan: completed
✓ Docker image built and tested locally
✓ Kubernetes manifests validated
✓ Database migrations verified
✓ Configuration properties set for environment
✓ Service dependencies available
✓ Monitoring/logging configured
✓ Health checks responding
✓ Performance baseline established
✓ Rollback plan documented
✓ Change request submitted
✓ Team notified
```

---

## QUICK REFERENCE

```bash
# Full pipeline: build → test → package → deploy
./gradlew clean build && \
docker build -t mca-cardcontrol:latest . && \
docker run -p 8080:8080 mca-cardcontrol:latest

# Development workflow
./gradlew bootRun --args='--spring.profiles.active=dev'

# CI/CD trigger
./gradlew build -x test  # Fast build for CI

# Production deployment
kubectl apply -f k8s-prod-deployment.yaml

# View all available tasks
./gradlew tasks --all
```

**Build Command Reference provides authoritative build and deployment guidance for MCA2 EPS applications.**

