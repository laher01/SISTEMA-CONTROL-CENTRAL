package online.factcentral.mobile;
import org.junit.Test;
import static org.junit.Assert.*;
public class EndpointConfigurationTest {
 @Test public void usesVerifiedHttpsApiHost(){
  assertEquals("https://app.nexomarnegocioseirl.online", Api.BASE);
 }
}
