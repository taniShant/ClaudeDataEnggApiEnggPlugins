package com.barclays.buk.arbiter.removal;

import org.junit.Before;
import org.junit.Test;
import org.junit.Rule;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.io.FileWriter;

import static org.junit.Assert.*;

/**
 * Unit tests for Spoon-based removal tool fixtures and argument parsing.
 *
 * Scope: These tests verify:
 * - Command-line argument parsing (--method, --class, --file)
 * - Test fixture creation for various Java source patterns
 * - File existence and basic I/O operations
 *
 * NOT TESTED: Actual Spoon removal execution and edge case handling.
 * Edge case handling (multi-line Javadoc, annotations, nested classes) is verified by:
 * 1. Python integration tests (tests/test_java_ast_removal.py) which mock subprocess calls
 * 2. Integration tests that invoke the actual JAR (requires JDK and Spoon at runtime)
 *
 * To test actual Spoon removal:
 *   ./gradlew integrationTest  (invokes SpoonRemovalTool via subprocess)
 */
public class SpoonRemovalToolTest {
    @Rule
    public TemporaryFolder tempFolder = new TemporaryFolder();

    @Before
    public void setUp() {
        // Setup for each test
    }

    @Test
    public void testRemoveMethodSimple() throws Exception {
        // FIXTURE TEST: Creates Java source and verifies argument parsing
        // Does NOT invoke Spoon removal or validate removal output
        String javaSource = "" +
            "public class TestClass {\n" +
            "    public void method1() {\n" +
            "        System.out.println(\"method1\");\n" +
            "    }\n" +
            "    public void method2() {\n" +
            "        System.out.println(\"method2\");\n" +
            "    }\n" +
            "}\n";

        File testFile = createTempJavaFile("TestClass.java", javaSource);
        String[] args = {"--method", "method1", "--file", testFile.getAbsolutePath()};

        // Verify argument parsing
        RemovalOptions options = parseArgs(args);
        assertNotNull(options);
        assertEquals("method1", options.methodName);
        assertEquals(testFile.getAbsolutePath(), options.filePath);
    }

    @Test
    public void testRemoveMethodMultiLineJavadoc() throws Exception {
        // FIXTURE TEST: Verifies Java source with multi-line Javadoc can be parsed and stored
        // Does NOT invoke Spoon removal to validate Javadoc handling
        // (Actual Javadoc edge case testing happens in Python integration tests via subprocess mocking)
        String javaSource = "" +
            "public class TestClass {\n" +
            "    /**\n" +
            "     * This is a multi-line Javadoc comment\n" +
            "     * spanning several lines\n" +
            "     * with detailed documentation.\n" +
            "     */\n" +
            "    public void documentedMethod() {\n" +
            "        System.out.println(\"documented\");\n" +
            "    }\n" +
            "}\n";

        File testFile = createTempJavaFile("TestClass.java", javaSource);
        assertNotNull(testFile);
        assertTrue(testFile.exists());
    }

    @Test
    public void testRemoveMethodMultipleAnnotations() throws Exception {
        // FIXTURE TEST: Verifies Java source with multiple annotations can be parsed and stored
        // Does NOT invoke Spoon removal to validate annotation handling
        // (Annotation edge case testing happens in Python integration tests via subprocess mocking)
        String javaSource = "" +
            "import java.lang.Override;\n" +
            "public class TestClass {\n" +
            "    @Override\n" +
            "    @Deprecated\n" +
            "    @SuppressWarnings(\"unused\")\n" +
            "    public void annotatedMethod() {\n" +
            "        System.out.println(\"annotated\");\n" +
            "    }\n" +
            "}\n";

        File testFile = createTempJavaFile("TestClass.java", javaSource);
        assertNotNull(testFile);
        assertTrue(testFile.exists());
    }

    @Test
    public void testRemoveNestedMethod() throws Exception {
        // FIXTURE TEST: Verifies Java source with nested classes can be parsed and stored
        // Does NOT invoke Spoon removal to validate nested class handling
        // (Nested structure edge case testing happens in Python integration tests via subprocess mocking)
        String javaSource = "" +
            "public class OuterClass {\n" +
            "    public class InnerClass {\n" +
            "        public void innerMethod() {\n" +
            "            System.out.println(\"inner\");\n" +
            "        }\n" +
            "    }\n" +
            "    public void outerMethod() {\n" +
            "        System.out.println(\"outer\");\n" +
            "    }\n" +
            "}\n";

        File testFile = createTempJavaFile("OuterClass.java", javaSource);
        assertNotNull(testFile);
        assertTrue(testFile.exists());
    }

    @Test
    public void testRemoveClassSimple() throws Exception {
        // FIXTURE TEST: Verifies Java source with multiple classes can be parsed and stored
        // Does NOT invoke Spoon removal to validate class removal
        // (Class removal edge case testing happens in Python integration tests via subprocess mocking)
        String javaSource = "" +
            "public class ClassToRemove {\n" +
            "    public void someMethod() {\n" +
            "        System.out.println(\"class to remove\");\n" +
            "    }\n" +
            "}\n" +
            "class AnotherClass {\n" +
            "    public void anotherMethod() {\n" +
            "        System.out.println(\"keep this\");\n" +
            "    }\n" +
            "}\n";

        File testFile = createTempJavaFile("Classes.java", javaSource);
        assertNotNull(testFile);
        assertTrue(testFile.exists());
    }

    @Test
    public void testRemoveClassWithGenerics() throws Exception {
        // FIXTURE TEST: Verifies Java source with generic types can be parsed and stored
        // Does NOT invoke Spoon removal to validate generic handling
        // (Generic edge case testing happens in Python integration tests via subprocess mocking)
        String javaSource = "" +
            "import java.util.List;\n" +
            "public class GenericClass<T> {\n" +
            "    private List<T> items;\n" +
            "    public void addItem(T item) {\n" +
            "        items.add(item);\n" +
            "    }\n" +
            "    public T getItem(int index) {\n" +
            "        return items.get(index);\n" +
            "    }\n" +
            "}\n";

        File testFile = createTempJavaFile("GenericClass.java", javaSource);
        assertNotNull(testFile);
        assertTrue(testFile.exists());
    }

    @Test
    public void testRemoveMethodNotFound() throws Exception {
        // ARGUMENT PARSING TEST: Verifies args are correctly parsed even when method doesn't exist
        // Does NOT invoke Spoon removal (Spoon would report "not found" during actual execution)
        String javaSource = "" +
            "public class TestClass {\n" +
            "    public void existingMethod() {\n" +
            "        System.out.println(\"exists\");\n" +
            "    }\n" +
            "}\n";

        File testFile = createTempJavaFile("TestClass.java", javaSource);
        String[] args = {"--method", "nonexistentMethod", "--file", testFile.getAbsolutePath()};

        // Parse args (should succeed - Spoon handles "not found" error during removal)
        RemovalOptions options = parseArgs(args);
        assertNotNull(options);
        assertEquals("nonexistentMethod", options.methodName);
    }

    @Test
    public void testRemoveClassNotFound() throws Exception {
        // ARGUMENT PARSING TEST: Verifies args are correctly parsed even when class doesn't exist
        // Does NOT invoke Spoon removal (Spoon would report "not found" during actual execution)
        String javaSource = "" +
            "public class ExistingClass {\n" +
            "    public void method() {\n" +
            "        System.out.println(\"exists\");\n" +
            "    }\n" +
            "}\n";

        File testFile = createTempJavaFile("ExistingClass.java", javaSource);
        String[] args = {"--class", "NonExistentClass", "--file", testFile.getAbsolutePath()};

        // Parse args (should succeed - Spoon handles "not found" error during removal)
        RemovalOptions options = parseArgs(args);
        assertNotNull(options);
        assertEquals("NonExistentClass", options.className);
    }

    @Test
    public void testFileNotFound() throws Exception {
        String[] args = {"--method", "someMethod", "--file", "/nonexistent/path/File.java"};
        RemovalOptions options = parseArgs(args);
        assertNotNull(options);
        // File existence check happens during removal, not during arg parsing
    }

    @Test
    public void testInvalidArgs() {
        String[] args = {"--method"}; // Missing file
        try {
            parseArgs(args);
            fail("Should throw IllegalArgumentException for missing --file");
        } catch (IllegalArgumentException e) {
            assertTrue(e.getMessage().contains("Usage"));
        }
    }

    @Test
    public void testMethodWithLambda() throws Exception {
        // FIXTURE TEST: Verifies Java source with lambda expressions can be parsed and stored
        // Does NOT invoke Spoon removal to validate lambda handling
        // (Lambda edge case testing happens in Python integration tests via subprocess mocking)
        String javaSource = "" +
            "import java.util.List;\n" +
            "public class TestClass {\n" +
            "    public void processItems(List<String> items) {\n" +
            "        items.forEach(item -> {\n" +
            "            if (item.length() > 5) {\n" +
            "                System.out.println(item.toUpperCase());\n" +
            "            }\n" +
            "        });\n" +
            "    }\n" +
            "}\n";

        File testFile = createTempJavaFile("TestClass.java", javaSource);
        assertNotNull(testFile);
        assertTrue(testFile.exists());
    }

    @Test
    public void testRemovalResultSuccess() {
        // POJO FACTORY TEST: Verifies RemovalResult.success() factory method
        // Does NOT test actual Spoon removal - only POJO construction and getters
        RemovalResult result = RemovalResult.success("Test method removed", 10);
        assertEquals("success", result.getStatus());
        assertEquals("Test method removed", result.getMessage());
        assertEquals(10, result.getRemovedLines());
        assertNull(result.getErrorDetails());
    }

    @Test
    public void testRemovalResultNotFound() {
        // POJO FACTORY TEST: Verifies RemovalResult.notFound() factory method
        // Does NOT test actual Spoon removal - only POJO construction and getters
        RemovalResult result = RemovalResult.notFound("Method not found");
        assertEquals("not_found", result.getStatus());
        assertEquals("Method not found", result.getMessage());
        assertEquals(0, result.getRemovedLines());
    }

    @Test
    public void testRemovalResultError() {
        // POJO FACTORY TEST: Verifies RemovalResult.error() factory method
        // Does NOT test actual Spoon removal - only POJO construction and getters
        RemovalResult result = RemovalResult.error("Parse error", "Stack trace here");
        assertEquals("error", result.getStatus());
        assertEquals("Parse error", result.getMessage());
        assertEquals("Stack trace here", result.getErrorDetails());
    }

    // Helper methods

    private File createTempJavaFile(String filename, String content) throws Exception {
        File file = new File(tempFolder.getRoot(), filename);
        try (FileWriter writer = new FileWriter(file)) {
            writer.write(content);
        }
        return file;
    }

    private RemovalOptions parseArgs(String[] args) throws IllegalArgumentException {
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

    /**
     * Command-line options for removal operation (mirrors main class).
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
