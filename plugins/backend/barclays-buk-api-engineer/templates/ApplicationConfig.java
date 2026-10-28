package {basePackage}.config;

import com.barclays.api.bap.bld.lib.logging.beans.SecureFields;
import com.barclays.api.bap.bld.lib.restapi.bootstrap.{ApiInitializer};
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.retry.annotation.EnableRetry;

/**
 * SDK3 Application Configuration.
 * Configures the {ApiInitializer} and SecureFields beans
 * required for the SDK3 framework to operate.
 * @EnableRetry activates Spring Retry support for all gateway methods
 * annotated with @Retryable.
 */
@Configuration
@EnableRetry
public class ApplicationConfig {

    @Bean
    public {ApiInitializer} apiInitializer() {
        return new {ApiInitializer}();
    }

    @Bean
    public SecureFields secureFields() {
        SecureFields secureFields = new SecureFields();
        secureFields.addNoLogSecureField("Authorization");
        secureFields.addNoLogSecureField("password");
        secureFields.addMaskSecureField("token", "*");
        secureFields.addMaskSecureField("accountNumber", "*");
        secureFields.addMaskSecureField("customerId", "*");
        secureFields.addMaskSecureField("email", "*");
        return secureFields;
    }
}
