package com.barclays.buk.arbiter.removal;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import spoon.Launcher;
import spoon.reflect.declaration.CtClass;
import spoon.reflect.declaration.CtMethod;
import spoon.reflect.declaration.CtType;

import java.io.File;
import java.util.Collection;

/**
 * Spoon-based Java code removal tool.
 *
 * Performs true AST transformation (not position-based string slicing).
 * Parses Java source → Modifies AST tree → Regenerates source.
 *
 * Usage:
 *   java -jar arbiter-removal-tool.jar --method methodName --file path/to/File.java
 *   java -jar arbiter-removal-tool.jar --class ClassName --file path/to/File.java
 *
 * Exit codes:
 *   0 = success
 *   1 = file not found or parse error
 *   2 = entity not found
 *   3 = other error
 */
public class SpoonRemovalTool {
    private static final Gson gson = new GsonBuilder().setPrettyPrinter().create();

    public static void main(String[] args) {
        try {
            RemovalOptions options = parseArgs(args);
            RemovalResult result = performRemoval(options);
            outputResult(result);
            System.exit(getExitCode(result));
        } catch (Exception e) {
            RemovalResult result = RemovalResult.error(
                "Unexpected error: " + e.getMessage(),
                e.toString()
            );
            outputResult(result);
            System.exit(3);
        }
    }

    private static RemovalOptions parseArgs(String[] args) throws IllegalArgumentException {
        String methodName = null;
        String className = null;
        String filePath = null;

        for (int i = 0; i < args.length; i++) {
            switch (args[i]) {
                case "--method":
                    if (i + 1 < args.length) methodName = args[++i];
                    break;
                case "--class":
                    if (i + 1 < args.length) className = args[++i];
                    break;
                case "--file":
                    if (i + 1 < args.length) filePath = args[++i];
                    break;
            }
        }

        if (filePath == null || (methodName == null && className == null)) {
            throw new IllegalArgumentException(
                "Usage: --method <name> --file <path> OR --class <name> --file <path>"
            );
        }

        return new RemovalOptions(methodName, className, filePath);
    }

    private static RemovalResult performRemoval(RemovalOptions options) {
        File sourceFile = new File(options.filePath);
        if (!sourceFile.exists()) {
            return RemovalResult.error(
                "File not found: " + options.filePath,
                null
            );
        }

        try {
            // Create Spoon launcher and build model
            Launcher launcher = new Launcher();
            launcher.addInputResource(options.filePath);
            launcher.setSourceClasspath(".");
            launcher.getEnvironment().setCommentEnabled(true);
            launcher.buildModel();

            if (options.methodName != null) {
                return removeMethod(launcher, options.methodName, sourceFile);
            } else {
                return removeClass(launcher, options.className, sourceFile);
            }
        } catch (Exception e) {
            return RemovalResult.error(
                "AST parsing or transformation failed: " + e.getMessage(),
                e.toString()
            );
        }
    }

    private static RemovalResult removeMethod(Launcher launcher, String methodName, File sourceFile) {
        Collection<CtType<?>> allTypes = launcher.getFactory().Type().getAll();

        boolean found = false;
        int removedLines = 0;

        for (CtType<?> type : allTypes) {
            if (type.isClass()) {
                CtClass<?> ctClass = (CtClass<?>) type;
                Collection<CtMethod<?>> methods = ctClass.getMethods();

                for (CtMethod<?> method : methods) {
                    if (method.getSimpleName().equals(methodName)) {
                        found = true;
                        // Calculate lines removed before deletion
                        int startLine = method.getPosition().getLine();
                        int endLine = method.getPosition().getEndLine();
                        removedLines = Math.max(1, endLine - startLine + 1);

                        // Remove method from parent class via AST modification
                        ctClass.removeMethod(method);
                    }
                }
            }
        }

        if (!found) {
            return RemovalResult.notFound("Method '" + methodName + "' not found");
        }

        // Write modified source back to file
        try {
            launcher.setSourceOutputDirectory(sourceFile.getParent());
            launcher.getEnvironment().setAutoImports(true);
            launcher.getEnvironment().setAutoUnbind(true);
            launcher.getEnvironment().setSourceClasspath(".");
            launcher.writeOutputModel();

            return RemovalResult.success(
                "Method '" + methodName + "' removed successfully",
                removedLines
            );
        } catch (Exception e) {
            return RemovalResult.error(
                "Failed to write modified source: " + e.getMessage(),
                e.toString()
            );
        }
    }

    private static RemovalResult removeClass(Launcher launcher, String className, File sourceFile) {
        Collection<CtType<?>> allTypes = launcher.getFactory().Type().getAll();

        boolean found = false;
        int removedLines = 0;

        for (CtType<?> type : allTypes) {
            if (type.getSimpleName().equals(className)) {
                found = true;
                // Calculate lines removed before deletion
                int startLine = type.getPosition().getLine();
                int endLine = type.getPosition().getEndLine();
                removedLines = Math.max(1, endLine - startLine + 1);

                // Remove class from compilation unit
                type.delete();
            }
        }

        if (!found) {
            return RemovalResult.notFound("Class '" + className + "' not found");
        }

        // Write modified source back to file
        try {
            launcher.setSourceOutputDirectory(sourceFile.getParent());
            launcher.getEnvironment().setAutoImports(true);
            launcher.getEnvironment().setAutoUnbind(true);
            launcher.getEnvironment().setSourceClasspath(".");
            launcher.writeOutputModel();

            return RemovalResult.success(
                "Class '" + className + "' removed successfully",
                removedLines
            );
        } catch (Exception e) {
            return RemovalResult.error(
                "Failed to write modified source: " + e.getMessage(),
                e.toString()
            );
        }
    }

    private static void outputResult(RemovalResult result) {
        String json = gson.toJson(result);
        System.out.println(json);
    }

    private static int getExitCode(RemovalResult result) {
        switch (result.getStatus()) {
            case "success":
                return 0;
            case "not_found":
                return 2;
            case "error":
                return 1;
            default:
                return 3;
        }
    }

    /**
     * Command-line options for removal operation.
     */
    private static class RemovalOptions {
        String methodName;
        String className;
        String filePath;

        RemovalOptions(String methodName, String className, String filePath) {
            this.methodName = methodName;
            this.className = className;
            this.filePath = filePath;
        }
    }
}
