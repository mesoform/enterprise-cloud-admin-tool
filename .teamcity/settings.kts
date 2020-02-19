import jetbrains.buildServer.configs.kotlin.v2018_2.BuildType
import jetbrains.buildServer.configs.kotlin.v2018_2.DslContext
import jetbrains.buildServer.configs.kotlin.v2018_2.buildFeatures.commitStatusPublisher
import jetbrains.buildServer.configs.kotlin.v2018_2.buildFeatures.freeDiskSpace
import jetbrains.buildServer.configs.kotlin.v2018_2.buildFeatures.swabra
import jetbrains.buildServer.configs.kotlin.v2018_2.buildSteps.dockerCommand
import jetbrains.buildServer.configs.kotlin.v2018_2.buildSteps.script
import jetbrains.buildServer.configs.kotlin.v2018_2.project
import jetbrains.buildServer.configs.kotlin.v2018_2.triggers.vcs
import jetbrains.buildServer.configs.kotlin.v2018_2.vcs.GitVcsRoot
import jetbrains.buildServer.configs.kotlin.v2018_2.version

/*
The settings script is an entry point for defining a TeamCity
project hierarchy. The script should contain a single call to the
project() function with a Project instance or an init function as
an argument.

VcsRoots, BuildTypes, Templates, and subprojects can be
registered inside the project using the vcsRoot(), buildType(),
template(), and subProject() methods respectively.

To debug settings scripts in command-line, run the

    mvnDebug org.jetbrains.teamcity:teamcity-configs-maven-plugin:generate

command and attach your debugger to the port 8000.

To debug in IntelliJ Idea, open the 'Maven Projects' tool window (View
-> Tool Windows -> Maven Projects), find the generate task node
(Plugins -> teamcity-configs -> teamcity-configs:generate), the
'Debug' option is available in the context menu for the task.
*/

version = "2018.2"

object GithubEcatVcs : GitVcsRoot({
    println("Evaluating the Git VCS root!\n")
    name = "GithubEcatVcs"
    url = "git@github.com:mesoform/enterprise-cloud-admin-tool.git"
    branch = "refs/heads/dev"
    branchSpec = """
        +:refs/pull/(*/merge)
    """.trimIndent()
    userNameStyle = GitVcsRoot.UserNameStyle.USERID
    checkoutSubmodules = GitVcsRoot.CheckoutSubmodules.SUBMODULES_CHECKOUT
    authMethod = uploadedKey {
        uploadedKey = "TeamCitySSH"
        userName = "git"
    }
})

project {
    vcsRoot(GithubEcatVcs)
    buildType(Build)

    println("Evaluating the project!\n")

    features {
        feature {
            id = "PROJECT_EXT_5"
            type = "IssueTracker"
            param("secure:password", "credentialsJSON:d34982db-19c6-4b1a-85ec-305cf20962c4")
            param("name", "mesoform/enterprise-cloud-admin")
            param("pattern", """#(\d+)""")
            param("authType", "loginpassword")
            param("repository", "https://bitbucket.org/mesoform/enterprise-cloud-admin")
            param("type", "BitBucketIssues")
            param("username", "cicd@mesoform.com")
        }
    }
}


object Build : BuildType({
    name = "Build"

    params {
        param("env.DOCKER_CONTAINER_ID", """""""")
        param("env.PYTHONPATH", ".:./tests")
    }

    vcs {
        root(GithubEcatVcs)

        cleanCheckout = true
    }

    steps {
        dockerCommand {
            name = "Build image"
            commandType = build {
                source = path {
                    path = "Dockerfile"
                }
                namesAndTags = "test_eca:latest"
                commandArgs = "--pull"
            }
        }
        dockerCommand {
            name = "Unit tests"
            commandType = other {
                subCommand = "run"
                commandArgs = "--name test_eca test_eca:latest pytest -v"
            }
        }
        script {
            name = "Tidy up"
            scriptContent = """
                docker rm test_eca
                docker system prune -a -f
                docker volume ls -qf dangling=true | xargs -r docker volume rm
            """.trimIndent()
        }
    }

    triggers {
        vcs {

        }
    }

    failureConditions {
        executionTimeoutMin = 30
    }

    features {
        commitStatusPublisher {
            publisher = github {
                githubUrl = "https://api.github.com"
                authType = personalToken {
                    token = "credentialsJSON:f9afb00d-2c25-4623-97ab-48f7bef9c6c1"
                }
            }
            param("secure:github_password", "credentialsJSON:142be9e9-8218-4985-a877-376ce3cf7a36")
            param("github_username", "gbmeuk")
        }
        freeDiskSpace {
            requiredSpace = "1gb"
            failBuild = false
        }
        swabra {
            forceCleanCheckout = true
        }
    }
})
