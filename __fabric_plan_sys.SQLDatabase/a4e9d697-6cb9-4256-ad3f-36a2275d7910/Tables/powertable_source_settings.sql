CREATE TABLE [a4e9d697-6cb9-4256-ad3f-36a2275d7910].[powertable_source_settings] (
    [id]        INT            IDENTITY (1, 1) NOT NULL,
    [sourceId]  INT            NULL,
    [name]      VARCHAR (255)  NOT NULL,
    [settings]  NVARCHAR (MAX) NOT NULL,
    [status]    INT            CONSTRAINT [DF_b9ef74fa4dcf80bd5d9e46eea24] DEFAULT ((10)) NOT NULL,
    [createdBy] NVARCHAR (128) NOT NULL,
    [updatedBy] NVARCHAR (128) NOT NULL,
    [createdAt] INT            NOT NULL,
    [updatedAt] INT            NOT NULL,
    CONSTRAINT [PK_86d8752dbe70afea9d1c924a502] PRIMARY KEY CLUSTERED ([id] ASC),
    CONSTRAINT [FK_aca67c695d159618d8bcdbc163f] FOREIGN KEY ([sourceId]) REFERENCES [a4e9d697-6cb9-4256-ad3f-36a2275d7910].[powertable_source] ([id])
);


GO

