"""Check all our redirects from remora to zamboni."""
from django import test


class TestRedirects(test.TestCase):

    fixtures = ['amo/test_redirects']

    def test_reviews(self):
        response = self.client.get('/reviews/display/4', follow=True)
        self.assertRedirects(response, '/en-US/firefox/addon/4/reviews/',
                             status_code=301)

    def test_browse(self):
        response = self.client.get('/browse/type:3', follow=True)
        self.assertRedirects(response, '/en-US/firefox/language-tools',
                             status_code=301)

    def test_accept_language(self):
        """
        Given an Accept Language header, do the right thing.  See bug 439568
        for juicy details.
        """

        # User wants de.  We send de
        response = self.client.get('/', follow=True, HTTP_ACCEPT_LANGUAGE='de')
        self.assertRedirects(response, '/de/firefox/', status_code=301)

        # User wants en-US, de.  We send en-US
        response = self.client.get('/', follow=True,
                                   HTTP_ACCEPT_LANGUAGE='en-us, de')
        self.assertRedirects(response, '/en-US/firefox/', status_code=301)

        # User wants fr, en.  We send fr
        response = self.client.get('/', follow=True,
                                   HTTP_ACCEPT_LANGUAGE='fr, en')
        self.assertRedirects(response, '/fr/firefox/', status_code=301)

        # User wants pt-XX, xx, yy.  We send pt-BR
        response = self.client.get('/', follow=True,
                                   HTTP_ACCEPT_LANGUAGE='pt-XX, xx, yy')
        self.assertRedirects(response, '/pt-BR/firefox/', status_code=301)

        # User wants pt.  We send pt-BR
        response = self.client.get('/', follow=True,
                                   HTTP_ACCEPT_LANGUAGE='pt')
        self.assertRedirects(response, '/pt-BR/firefox/', status_code=301)

        # User wants pt, de.  We send de
        response = self.client.get('/', follow=True,
                                   HTTP_ACCEPT_LANGUAGE='pt, de')
        self.assertRedirects(response, '/de/firefox/', status_code=301)

        # User wants pt-XX, xx, de.  We send de
        response = self.client.get('/', follow=True,
                                   HTTP_ACCEPT_LANGUAGE='pt-XX, xx, de')
        self.assertRedirects(response, '/de/firefox/', status_code=301)

        # User wants de-XX, xx, en-XX.  We send de
        response = self.client.get('/', follow=True,
                                   HTTP_ACCEPT_LANGUAGE='pt-XX, xx, de')
        self.assertRedirects(response, '/de/firefox/', status_code=301)

        # User wants xx, yy, zz.  We send en-US
        response = self.client.get('/', follow=True,
                                   HTTP_ACCEPT_LANGUAGE='xx, yy, zz')
        self.assertRedirects(response, '/en-US/firefox/', status_code=301)

        # User wants some,thing-very;very,,,broken!\'jj.  We send en-US
        response = self.client.get('/', follow=True,
                   HTTP_ACCEPT_LANGUAGE='some,thing-very;very,,,broken!\'jj')
        self.assertRedirects(response, '/en-US/firefox/', status_code=301)

        # User wants en-US;q=0.5, de.  We send de
        response = self.client.get('/', follow=True,
                                   HTTP_ACCEPT_LANGUAGE='en-us;q=0.5, de')
        self.assertRedirects(response, '/de/firefox/', status_code=301)

    def test_users(self):
        response = self.client.get('/users/info/1', follow=True)
        self.assertRedirects(response, '/en-US/firefox/user/1/',
                             status_code=301)
