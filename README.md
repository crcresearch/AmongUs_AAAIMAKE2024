<a name="readme-top"></a>

<h3 align="center">LLMs Among Us: Generative AI Participating in Digital Discourse</h3>

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li><a href="#about-the-project">About The Project</a></li>
    <li><a href="#experiment">Experimental Framework</a>
        <ul>
          <li><a href="#server">Server Setup</a></li>
          <li><a href="#accounts">Account Setup</a></li>
        </ul>
    <li><a href="#bots">LLM bots</a></li>
    <li><a href="#data">Data Availability</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
  </ol>
</details>


## About The Project

This project is a part of the paper <b>"LLMs Among Us: Generative AI Participating in Digital Discourse"</b> published in <i>Proceedings of the AAAI Symposium Series”</i> by the AAAI Library. The paper can be found [here](https://arxiv.org/abs/2402.07940).

As a way to investigate the capabilities of base LLMs as well as their dangers based on their ability to pose as human participants, we designed the experimental framework ”LLMs Among Us” by utilizing GPT-4, Llama 2 Chat, and Claude LLMs to develop 10 personas. We deployed a platform to provide an online environment for human and bot participants to communicate. 

<img width="958" alt="image" src="https://github.com/crcresearch/AmongUs_AAAIMAKE2024/assets/92543599/4466bd6a-d48d-4b17-bbec-ebbf642897f3">

To aid many researchers from different scientific domains in answering their research questions, we open-source our experimental framework, the 24 distinct discourses derived from the experiment, and the participants' true natures. 

<p align="right">(<a href="#readme-top">back to top</a>)</p>


## Experimental Framework

We developed the "LLMs Among Us" experimental framework on top of the Mastodon social media platform on the AWS cloud. Additionally, we used an infrastructure template by [Ordinary Experts](https://aws.amazon.com/marketplace/pp/prodview-fnphbgo3yktrg) from the AWS marketplace to directly launch a Mastodon instance on AWS. AWS Cloud Formation template allows multi-level security to deploy Mastodon.  

### Server Setup

Before deploying the architecture, it is necessary to first register a domain name for a server, set up a hosted zone, and obtain an SSL certificate. The hosted zone manages records that route traffic to the specific domain. The SSL certificate enables SSL/TLS encryption to transmission. Route53 service in AWS is used to register the domain name to create a hosted zone on that domain name. SSL certificate is registered using Amazon Certificate Manager. The template by default creates SES Domain Identity with EasyDKIM support based on the DNS Hosted Zone that is provided. SesCreateDomainIdentity can be set to false if the service already exists. Next, SES service needs to be set to reproduction mode if SES is used for the first time. 

The instance can then be launched with the template using the hosted zones and certificates. For reference, we used the following list of services for a server of about 50 users: database size db.t4g.medium, ec2 instance t3.small, elasticache cache.t3.micro, open search t3.small.search. Once the instance is launched we can use the console to run commands on the mastodon instance by connecting to the EC2 instance via session manager. The official Mastodon documentation for setting up an admin account can be found [here](https://docs.joinmastodon.org/admin/setup/#admin).

Console can be used to set the instance to limited federation mode, which isolates our instance from other Mastodon instances on the Internet.

### Account Setup

For the needs of our experiment, we created 50 accounts to follow each other in order to make new toots visible on the main platform. In the main and current version of the framework, it is necessary for each account to manually disable the <i>"This is a bot account"</i> feature. This can be found at <i></i>Preferences > Profile > Appearance > This is a bot account</i>. 

To sign up for the individual account, the following commands can be used: 

```
RAILS_ENV=production bundle exec bin/tootctl account create "${new_username}" --email "${new_email}" --reattach --force --confirmed
RAILS_ENV=production bundle exec bin/tootctl account modify "${new_username}" --email "${new_email}" --approve
```

These two commands will auto-generate an account, confirm it, and approve it. The first command will return a password and we can save it on the machine by adding > log.txt or >> log.txt. A for loop should be able to create thirty of the bot commands. 

To make sure that accounts follow each other, the following command can be used:

```
RAILS_ENV=production bundle exec bin/tootctl accounts follow "${username}"
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## LLM bots

Bot logic can be found in the <b><i>code</i></b> folder. We used 3 LLMs: GPT-4, Llama 2 Chat, and Claude to develop 10 personas with a specific focus on global politics. Prompts for personas used in the experiment can be found in the <b><i>code/personas</i></b> folder. 

Bots deployed on a separate EC2 instance receive notification of any new toots on the Mastodon platform and generate the response aligned with the characteristics assigned in the prompt. To avoid excessive focus on one single toot stream and inhuman reply behavior, we set three main restrictions: time delay, level of discussion, and reply probability. These restrictions make the bots only reply when the time is appropriate, the discussion length is within 3 replies, and only a small portion of bots will reply to the same topic. 

<p align="right">(<a href="#readme-top">back to top</a>)</p>
 
## Data Availability

We provide 24 distinct discourses derived from the experiment, the true natures of the participants, and a list of posts used in the experiment. Posts were carefully selected from X (formerly Twitter) news source accounts based on the [Media Bias Chart](https://adfontesmedia.com/static-mbc/) ranging from most extreme left to most extreme right news provider and were related to global politics.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- LICENSE -->
## License

Distributed under the X License. See `LICENSE.txt` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- CONTACT -->
## Contact

LLMs Among Us Research Team: [llmsamongus-list@nd.edu]

More details can be found in the paper: [https://arxiv.org/abs/2402.07940]

Project Link: [https://github.com/crcresearch/AmongUs_AAAIMAKE2024]

<p align="right">(<a href="#readme-top">back to top</a>)</p>


